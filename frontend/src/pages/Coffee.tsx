import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Coffee, Sprout, Sparkles, ChevronRight, Star, ArrowLeft } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import PageHeader from '@/components/ui/PageHeader.tsx'
import {
  completeCoffee,
  CoffeeTodayResponse,
  getCoffeeToday,
  saveCoffeeProgress,
} from '../api/client'

function extractApiMessage(error: any): { message: string; ctaPath?: string } {
  const detail = error?.response?.data?.detail

  if (detail && typeof detail === 'object') {
    return {
      message: String(detail.message || 'Что-то пошло не так. Давай попробуем ещё раз.'),
      ctaPath: detail.cta_path ? String(detail.cta_path) : undefined,
    }
  }

  if (typeof detail === 'string' && detail.trim()) {
    return { message: detail }
  }

  return { message: 'Что-то пошло не так. Давай попробуем ещё раз.' }
}

export default function CoffeePage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [today, setToday] = useState<CoffeeTodayResponse | null>(null)

  const [step, setStep] = useState(0)
  const [rejoiced, setRejoiced] = useState<string[]>([])
  const [notesDraft, setNotesDraft] = useState('')

  const [completeProjectDay, setCompleteProjectDay] = useState(true)
  const [completedTaskIds, setCompletedTaskIds] = useState<string[]>([])

  const [error, setError] = useState<string | null>(null)
  const [ctaPath, setCtaPath] = useState<string | null>(null)

  const notesDebounceTimer = useRef<number | null>(null)

  const steps = useMemo(
    () => [
      {
        title: '🧘 Подготовка',
        desc: 'Сделай пару спокойных вдохов. Давай мягко вспомним всё хорошее, что уже случилось сегодня.',
      },
      {
        title: '🌱 День',
        desc: 'Посмотри на свои шаги и семена. Это твоя опора — ты уже продвинулся(лась).',
      },
      {
        title: '☕️ Радость',
        desc: 'Выбери семена, за которые хочется порадоваться. Радость усиливает их и помогает им быстрее прорасти.',
      },
      {
        title: '✨ Посвящение',
        desc: 'Добавь пару слов для себя — и, если хочешь, закрой день проекта мягко и уверенно.',
      },
    ],
    []
  )

  const dailyTasks = today?.daily_plan?.tasks || []
  const seeds = today?.seeds || []

  const progress = ((step + 1) / steps.length) * 100

  const persistProgress = async (next: { step?: number; notesDraft?: string; rejoiced?: string[] }) => {
    setError(null)
    setCtaPath(null)

    const payload = {
      current_step: next.step ?? step,
      notes_draft: next.notesDraft ?? notesDraft,
      rejoiced_seed_ids: next.rejoiced ?? rejoiced,
    }

    try {
      await saveCoffeeProgress(payload)
    } catch (e: any) {
      const parsed = extractApiMessage(e)
      setError(parsed.message)
      if (parsed.ctaPath) setCtaPath(parsed.ctaPath)
    }
  }

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true)
        setError(null)
        setCtaPath(null)

        const data = await getCoffeeToday()
        setToday(data)

        const session = data.session
        if (session) {
          setStep(Number.isFinite(session.current_step) ? session.current_step : 0)
          setRejoiced(session.rejoiced_seed_ids || [])
          setNotesDraft(session.notes_draft || '')
        }

        if (data.daily_plan?.tasks) {
          const initialCompleted = data.daily_plan.tasks
            .filter((t) => t.completed)
            .map((t) => t.id)
          setCompletedTaskIds(initialCompleted)
        }
      } catch (e: any) {
        const parsed = extractApiMessage(e)
        setError(parsed.message)
        setCtaPath(parsed.ctaPath || null)
      } finally {
        setLoading(false)
      }
    }

    load()

    return () => {
      if (notesDebounceTimer.current) {
        window.clearTimeout(notesDebounceTimer.current)
      }
    }
  }, [])

  const toggleRejoice = (id: string) => {
    setRejoiced((prev) => {
      const next = prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
      void persistProgress({ rejoiced: next })
      return next
    })
  }

  const toggleTask = (id: string) => {
    setCompletedTaskIds((prev) => (prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]))
  }

  const handleNext = () => {
    if (step < steps.length - 1) {
      const nextStep = step + 1
      setStep(nextStep)
      void persistProgress({ step: nextStep })
      return
    }

    void (async () => {
      try {
        setError(null)
        setCtaPath(null)

        await completeCoffee({
          rejoiced_seed_ids: rejoiced,
          notes: notesDraft || undefined,
          complete_project_day: completeProjectDay,
          completed_task_ids: completedTaskIds,
        })

        navigate('/')
      } catch (e: any) {
        const parsed = extractApiMessage(e)
        setError(parsed.message)
        if (parsed.ctaPath) setCtaPath(parsed.ctaPath)
      }
    })()
  }

  const handleBack = () => {
    if (step <= 0) {
      navigate('/')
      return
    }

    const nextStep = step - 1
    setStep(nextStep)
    void persistProgress({ step: nextStep })
  }

  const onNotesChange = (value: string) => {
    setNotesDraft(value)

    if (notesDebounceTimer.current) {
      window.clearTimeout(notesDebounceTimer.current)
    }

    notesDebounceTimer.current = window.setTimeout(() => {
      void persistProgress({ notesDraft: value })
    }, 500)
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin text-white/70">
          <Coffee className="h-8 w-8" />
        </div>
      </div>
    )
  }

  if (error && ctaPath) {
    return (
      <div className="min-h-screen flex flex-col p-4 pb-10">
        <div className="flex-1 flex flex-col justify-center max-w-md mx-auto w-full gap-6">
          <Card className="shadow-soft overflow-hidden relative">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-orange-400 to-rose-500" />
            <CardContent className="p-6 text-center space-y-4 pt-8">
              <div className="inline-flex p-3 rounded-full bg-white/10 border border-white/20">
                <Coffee className="h-8 w-8 text-orange-200" />
              </div>
              <p className="text-base leading-relaxed text-white">{error}</p>
              <Button
                className="w-full h-12 font-semibold rounded-full bg-gradient-to-r from-orange-400 to-rose-500 hover:from-orange-500 hover:to-rose-600 border-0 text-white"
                onClick={() => navigate(ctaPath)}
              >
                Собрать проект
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6 p-4 max-w-3xl mx-auto w-full pb-28 relative">
      <div className="flex items-center justify-between mt-2">
        <Button variant="ghost" className="px-2" onClick={handleBack}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="text-[10px] font-semibold uppercase tracking-widest text-white/60">
          Шаг {step + 1} из {steps.length}
        </div>
        <div className="w-10" />
      </div>

      <div className="space-y-2">
        <PageHeader text="Кофе-медитация" icon={Coffee} />
        <p className="text-sm text-white/60">Усиль семена через радость и посвяти результат — мягко, без спешки.</p>
        <div className="h-2 w-full bg-white/10 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-orange-400 to-rose-500 transition-all"
            style={{ width: `${Math.max(0, Math.min(100, progress))}%` }}
          />
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm font-medium border border-destructive/20">
          {error}
        </div>
      )}

      <Card className="shadow-soft overflow-hidden relative">
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-orange-400 to-rose-500" />
        <CardContent className="p-6 space-y-5 pt-8">
          <div className="flex items-start gap-4">
            <div className="h-12 w-12 rounded-2xl bg-white/10 border border-white/20 flex items-center justify-center shrink-0 text-2xl">
              {steps[step].title.split(' ')[0]}
            </div>
            <div className="flex-1 space-y-1 min-w-0">
              <h2 className="text-lg font-semibold text-white">
                {steps[step].title.split(' ').slice(1).join(' ')}
              </h2>
              <p className="text-sm leading-relaxed text-white/70">{steps[step].desc}</p>
            </div>
          </div>

          {step === 1 && (
            <div className="space-y-5 animate-in fade-in slide-in-from-bottom-4 duration-500">
              {dailyTasks.length > 0 ? (
                <div className="space-y-2">
                  <div className="text-xs font-bold uppercase tracking-wider text-white/60">Твои шаги на сегодня</div>
                  <div className="space-y-2">
                    {dailyTasks.map((t) => (
                      <div
                        key={t.id}
                        className={cn(
                          'rounded-2xl border p-4 flex items-start gap-3 backdrop-blur-main',
                          t.completed
                            ? 'bg-white/15 border-white/25'
                            : 'bg-white/10 hover:bg-white/15 border-white/20'
                        )}
                      >
                        <div
                          className={cn(
                            'h-9 w-9 rounded-full flex items-center justify-center shrink-0 border',
                            t.completed
                              ? 'bg-green-500/15 border-green-400/30 text-green-200'
                              : 'bg-white/10 border-white/20 text-white/70'
                          )}
                        >
                          {t.completed ? <Star className="h-4 w-4 fill-current" /> : <Sprout className="h-4 w-4" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-white">{t.description}</p>
                          {t.why && <p className="text-xs text-white/60 mt-1">{t.why}</p>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-center p-4 italic bg-white/10 rounded-2xl border border-white/20 backdrop-blur-main text-white/70">
                  На сегодня нет списка шагов — ничего страшного. Даже маленькое доброе действие уже считается.
                </div>
              )}

              <div className="space-y-2">
                <div className="text-xs font-bold uppercase tracking-wider text-white/60">Семена за сегодня</div>

                {seeds.length === 0 ? (
                  <div className="text-center p-4 italic bg-white/10 rounded-2xl border border-white/20 backdrop-blur-main text-white/70">
                    Сегодня семян ещё нет. Если хочешь — просто вспомни любое доброе дело, даже самое небольшое.
                  </div>
                ) : (
                  <div className="space-y-2 max-h-[240px] overflow-y-auto pr-1 scrollbar-none">
                    {seeds.map((s) => (
                      <div
                        key={s.id}
                        className="p-4 rounded-2xl border bg-white/10 border-white/20 flex items-center gap-3 backdrop-blur-main"
                      >
                        <div className="h-9 w-9 rounded-full bg-white/10 border border-white/20 flex items-center justify-center shrink-0 text-white/70">
                          <Sprout className="h-5 w-5" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-white truncate">{s.description}</p>
                          {typeof s.rejoice_count === 'number' && (
                            <p className="text-[11px] text-white/60 mt-1">Радость: {s.rejoice_count}</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-3 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="text-xs font-bold uppercase tracking-wider text-white/60">Выбери семена для радости</div>

              {seeds.length === 0 && (
                <div className="text-center p-4 italic bg-white/10 rounded-2xl border border-white/20 backdrop-blur-main text-white/70">
                  Сегодня семян ещё нет. Если хочется — ты можешь посадить семя в «Журнале».
                </div>
              )}

              <div className="space-y-3 max-h-[300px] overflow-y-auto pr-1 scrollbar-none">
                {seeds.map((s) => {
                  const isRejoiced = rejoiced.includes(s.id)
                  return (
                    <div
                      key={s.id}
                      onClick={() => toggleRejoice(s.id)}
                      className={cn(
                        'p-4 rounded-2xl border transition-all cursor-pointer flex items-center gap-3 relative overflow-hidden group backdrop-blur-main',
                        isRejoiced
                          ? 'bg-orange-500/10 border-orange-400/30 shadow-sm'
                          : 'bg-white/10 hover:bg-white/15 border-white/20 hover:border-white/35'
                      )}
                    >
                      <div
                        className={cn(
                          'h-10 w-10 rounded-full flex items-center justify-center shrink-0 transition-colors border',
                          isRejoiced
                            ? 'bg-orange-500/15 border-orange-400/30 text-orange-200'
                            : 'bg-white/10 border-white/20 text-white/70'
                        )}
                      >
                        {isRejoiced ? (
                          <Star className="h-5 w-5 fill-current" />
                        ) : (
                          <Sprout className="h-5 w-5" />
                        )}
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          {isRejoiced && (
                            <span className="text-xs font-bold text-orange-200 animate-in fade-in zoom-in">РАДОСТЬ!</span>
                          )}
                          {typeof s.rejoice_count === 'number' && (
                            <span className="text-[10px] text-white/60">{s.rejoice_count} раз(а)</span>
                          )}
                        </div>
                        <p className="text-sm font-medium text-white truncate">{s.description}</p>
                      </div>

                      {isRejoiced && <div className="absolute right-0 top-0 bottom-0 w-1 bg-orange-400" />}
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-5 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="space-y-2">
                <Label className="text-white">Пара тёплых слов для себя</Label>
                <Textarea
                  value={notesDraft}
                  onChange={(e) => onNotesChange(e.target.value)}
                  placeholder="Например: Сегодня я молодец(умница), потому что..."
                  className="min-h-[110px]"
                />
                <p className="text-xs text-white/60">Мы сохраняем это мягко, по мере того как ты пишешь.</p>
              </div>

              {dailyTasks.length > 0 && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between gap-4">
                    <Label className="text-white">Какие шаги ты сделал(а) сегодня?</Label>
                    <div className="flex items-center gap-2">
                      <Checkbox
                        id="complete_project_day"
                        checked={completeProjectDay}
                        onCheckedChange={(c) => setCompleteProjectDay(Boolean(c))}
                      />
                      <Label htmlFor="complete_project_day" className="text-sm font-normal cursor-pointer">
                        Закрыть день
                      </Label>
                    </div>
                  </div>

                  <div className="space-y-2">
                    {dailyTasks.map((t) => {
                      const checked = completedTaskIds.includes(t.id)
                      return (
                        <div
                          key={t.id}
                          className={cn(
                            'p-4 rounded-2xl border bg-white/10 border-white/20 flex items-start gap-3 backdrop-blur-main'
                          )}
                        >
                          <Checkbox
                            id={`task_${t.id}`}
                            checked={checked}
                            onCheckedChange={() => toggleTask(t.id)}
                            className="mt-1"
                          />
                          <div className="flex-1 min-w-0">
                            <Label htmlFor={`task_${t.id}`} className="text-sm font-medium cursor-pointer">
                              {t.description}
                            </Label>
                            {t.why && <p className="text-xs text-white/60 mt-1">{t.why}</p>}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}

              {dailyTasks.length === 0 && (
                <div className="flex items-center gap-2 text-white">
                  <Checkbox
                    id="complete_project_day_empty"
                    checked={completeProjectDay}
                    onCheckedChange={(c) => setCompleteProjectDay(Boolean(c))}
                  />
                  <Label htmlFor="complete_project_day_empty" className="text-sm font-normal cursor-pointer">
                    Закрыть день проекта
                  </Label>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="fixed bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/60 to-transparent backdrop-blur-sm">
        <div className="max-w-3xl mx-auto w-full">
          <Button
            onClick={handleNext}
            className="w-full h-12 text-base font-semibold rounded-full shadow-sm bg-gradient-to-r from-orange-400 to-rose-500 hover:from-orange-500 hover:to-rose-600 border-0 text-white"
          >
            {step === steps.length - 1 ? (
              <>
                Завершить
                <Sparkles className="ml-2 h-5 w-5" />
              </>
            ) : (
              <>
                Далее
                <ChevronRight className="ml-2 h-5 w-5" />
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}
