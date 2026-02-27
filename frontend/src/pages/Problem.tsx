import { FormEvent, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  solveProblem,
  getProblemsHistory,
  getPartners,
  addProblemToCalendar,
  getActiveProject,
  ProjectStatusResponse
} from '../api/client'
import ActiveProjectDashboard from '../components/ActiveProjectDashboard'
import PartnerWizard from '../components/PartnerWizard'
import { Loader2, Sparkles, Brain, Search, History, CheckCircle2, AlertCircle, Calendar, Target, ArrowRight, Lightbulb, ChevronRight, ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import PageHeader from "@/components/ui/PageHeader.tsx";

export default function Problem() {
  const navigate = useNavigate()
  const [problem, setProblem] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const [history, setHistory] = useState<any[]>([])
  const [partners, setPartners] = useState<any[]>([])
  const [selectedPartners, setSelectedPartners] = useState<string[]>([])
  const [showHistory, setShowHistory] = useState(false)
  // Режим уточняющих вопросов (Q&A), если агенту не хватает ясности
  const [needsClarification, setNeedsClarification] = useState(false)
  const [clarifyingQuestions, setClarifyingQuestions] = useState<string[]>([])
  const [clarificationText, setClarificationText] = useState('')
  const [initialProblem, setInitialProblem] = useState('')
  const [sessionId, setSessionId] = useState<string | null>(null)
  
  const [activeProjectData, setActiveProjectData] = useState<ProjectStatusResponse | null>(null)
  const [showProblemForm, setShowProblemForm] = useState(true)
  const [showWizard, setShowWizard] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)
  const [wizardHistoryId, setWizardHistoryId] = useState<string | null>(null)

  const loadData = async () => {
    try {
      const [histData, partData, projData] = await Promise.all([
        getProblemsHistory(),
        getPartners(),
        getActiveProject()
      ])
      setHistory(histData.history || [])
      setPartners(partData.partners || [])
      setActiveProjectData(projData)
      
      // If we have an active project, hide the form by default
      if (projData && projData.has_active_project) {
        setShowProblemForm(false)
      } else {
        setShowProblemForm(true)
      }

      // Auto-open partner wizard if active project lacks required partners
      if (projData && projData.has_active_project && projData.project) {
        const partnersByCategory = projData.project.partners || {}
        const isolation = projData.project.isolation_settings || {}
        const categories = ['source', 'ally', 'protege', 'world']
        const hasMissingPartners = categories.some((cat) => {
          const catIsolation = isolation[cat]?.is_isolated
          const catPartners = partnersByCategory[cat] || []
          return !catIsolation && catPartners.length === 0
        })

        if (hasMissingPartners && projData.project.history_id) {
          setWizardHistoryId(projData.project.history_id)
          setShowWizard(true)
          setShowProblemForm(false)
        }
      }
    } catch (e) {
      console.error('Failed to load data', e)
    } finally {
      setInitialLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!problem.trim()) return

    try {
      setError(null)
      setSuccess(null)
      setLoading(true)
      const currentProblem = problem.trim()
      const data = await solveProblem({ problem: currentProblem })

      // Если агент просит уточнения и дал 1–3 вопроса — переходим в режим уточнения
      if (data?.needs_clarification && Array.isArray(data.clarifying_questions) && data.clarifying_questions.length > 0) {
        setNeedsClarification(true)
        setClarifyingQuestions(data.clarifying_questions.slice(0, 3))
        setClarificationText('')
        setInitialProblem(currentProblem)
        setSessionId(data.session_id || null)
        setResult(null)
      } else {
        setResult(data)
        setSessionId(data.session_id || null)
        await loadData() // Refresh history (and grab new history_id if needed)
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to solve problem')
    } finally {
      setLoading(false)
    }
  }

  const onClarificationSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!clarificationText.trim()) return

    try {
      setError(null)
      setSuccess(null)
      setLoading(true)

      if (!sessionId) {
        setError('Сессия диагностики утеряна. Попробуй начать заново.')
        setNeedsClarification(false)
        setClarifyingQuestions([])
        return
      }

      const baseProblem = initialProblem || problem.trim()

      const data = await solveProblem({
        problem: baseProblem,
        session_id: sessionId,
        diagnostic_answer: clarificationText.trim()
      })

      // Check if the agent needs MORE clarification (multi-step diagnostic)
      if (data?.needs_clarification && Array.isArray(data.clarifying_questions) && data.clarifying_questions.length > 0) {
        setNeedsClarification(true)
        setClarifyingQuestions(data.clarifying_questions.slice(0, 3))
        setClarificationText('')
        setSessionId(data.session_id || sessionId)
        // Keep result null so we don't show empty dashboard
        setResult(null)
      } else {
        // Diagnostic complete - show final solution
        setResult(data)
        setNeedsClarification(false)
        setClarifyingQuestions([])
        setClarificationText('')
        setSessionId(data.session_id || sessionId)
        await loadData()
      }
    } catch (err: any) {
      setError(err?.message || 'Не удалось обработать уточнения')
    } finally {
      setLoading(false)
    }
  }

  const handleActivateHistory = async (h: any) => {
    // Выбираем проблему из истории: показываем решение и обновляем фокус без отдельного эндпоинта
    try {
      setLoading(true)
      setError(null)

      setResult(h.solution)
      // Ensure result has history_id for project activation
      setResult((prev: any) => ({ ...prev, history_id: h.id }))

      setProblem(h.problem_text)

      setSuccess('Проблема выбрана из истории.')
      setShowHistory(false)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } catch (err: any) {
      setError('Не удалось открыть проблему из истории')
    } finally {
      setLoading(false)
    }
  }
  
  const handleStartProject = () => {
    if (!result || !result.history_id) {
      setError('Невозможно создать проект: отсутствует ID истории. Попробуйте обновить страницу.')
      return
    }
    setWizardHistoryId(result.history_id)
    setShowWizard(true)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleWizardComplete = (projData: ProjectStatusResponse) => {
    setActiveProjectData(projData)
    setSuccess('🚀 Кармический проект успешно запущен! Твой план на 30 дней готов.')
    setResult(null)
    setShowProblemForm(false)
    setShowWizard(false)
    setWizardHistoryId(null)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleWizardCancel = () => {
    setShowWizard(false)
    setWizardHistoryId(null)
  }

  const togglePartner = (id: string) => {
    setSelectedPartners(prev =>
      prev.includes(id) ? prev.filter(p => p !== id) : [...prev, id]
    )
  }

  const handleStartPractice = () => {
    if (!result) return;
    const desc = encodeURIComponent(`STOP: ${result.stop_action}\nSTART: ${result.start_action}`);
    const parts = selectedPartners.length > 0 ? `&partner_ids=${selectedPartners.join(',')}` : '';
    navigate(`/journal?description=${desc}${parts}`);
  };

  const handleAddToCalendar = async () => {
    if (!result?.practice_steps) return;
    try {
      setLoading(true);
      await addProblemToCalendar(result.practice_steps);
      setSuccess('План на 30 дней успешно добавлен в твой календарь! 📅');
    } catch (err) {
      setError('Не удалось добавить план в календарь');
    } finally {
      setLoading(false);
    }
  };

  const renderContent = (text: string) => {
    if (!text) return null;
    return <div className="whitespace-pre-wrap">{text}</div>;
  };

  if (initialLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className=" text-sm">Загружаем кармическую историю...</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6 p-4 max-w-3xl mx-auto w-full pb-24">
      <div className="space-y-1 mt-2">
		  <PageHeader text="Решение проблемы" icon={Brain}/>
        {/*<h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-3">*/}
        {/*  <Brain className="h-8 w-8 text-primary" />*/}
        {/*  */}
        {/*</h1>*/}
        <p className=" leading-relaxed">
          Система проанализирует запрос и предложит кармический путь исправления.
        </p>
      </div>

      {showWizard && wizardHistoryId ? (
        <PartnerWizard 
          historyId={wizardHistoryId}
          onComplete={handleWizardComplete}
          onCancel={handleWizardCancel}
          existingPartners={
            activeProjectData?.project && activeProjectData.project.history_id === wizardHistoryId
              ? activeProjectData.project.partners
              : undefined
          }
          existingIsolation={
            activeProjectData?.project && activeProjectData.project.history_id === wizardHistoryId
              ? activeProjectData.project.isolation_settings
              : undefined
          }
        />
      ) : (
        <>
          {/* ACTIVE PROJECT DASHBOARD */}
          {activeProjectData?.has_active_project && activeProjectData.project && (
            <div className="space-y-6">
              <ActiveProjectDashboard data={activeProjectData} onRefresh={loadData} />
              
              {!showProblemForm && (
                <Button 
                  variant="outline" 
                  className="w-full border-dashed"
                  onClick={() => setShowProblemForm(true)}
                >
                  <Search className="h-4 w-4 mr-2" />
                  Разобрать другую проблему (не прерывая проект)
                </Button>
              )}
            </div>
          )}

          {/* PROBLEM FORM */}
          {showProblemForm && (
            <div className="space-y-6">
              {needsClarification && clarifyingQuestions.length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Search className="h-5 w-5" />
                      Нужно чуть больше деталей
                    </CardTitle>
                    <CardDescription>
                      Ответь одним сообщением на вопросы ниже — так система сможет точнее увидеть корень проблемы.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
						{!loading && (
							<div className="p-4 border-1 bg-orange-600/20 border-orange-600/40 space-y-2 rounded-md">
								{clarifyingQuestions.map((q, idx) => (
									<p key={idx} className="text-sm font-medium">{q}</p>
								))}
							</div>
						)}

                      <form onSubmit={onClarificationSubmit} className="space-y-4">
                        {!loading && <Textarea
                          value={clarificationText}
                          onChange={(e) => setClarificationText(e.target.value)}
                          placeholder="Напиши свои ответы одним сообщением..."
                          className="min-h-[100px] "
                        />}
                        <Button 
                          type="submit" 
                          disabled={loading || !clarificationText.trim()}
                          className="w-full bg-orange-600 hover:bg-orange-700"
                        >
                          {loading ? (
                            <>
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                              Анализирую уточнения...
                            </>
                          ) : 'Отправить уточнения'}
                        </Button>
                      </form>
                    </div>
                  </CardContent>
                </Card>
              )}

              {!needsClarification && (
                <form onSubmit={onSubmit} className="space-y-4">
                  <Textarea
                    value={problem}
                    onChange={(e) => setProblem(e.target.value)}
                    placeholder="Опиши проблему как можно точнее..."
                    className="min-h-[120px] text-base resize-y "
                  />
                  <Button 
                    type="submit" 
                    className="w-full py-6 text-lg" 
                    disabled={loading || !problem.trim()}
                  >
                    {loading ? (
                      <>
                        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                        Анализирую отпечатки...
                      </>
                    ) : (
                      <>
                        <Sparkles className="mr-2 h-5 w-5" />
                        Найти решение
                      </>
                    )}
                  </Button>
                </form>
              )}
            </div>
          )}
          
          {/* HISTORY SECTION - Always visible or collapsable */}
          {history.length > 0 && !needsClarification && !result && (
            <div className="space-y-2 pt-4 border-t border-white/20">
              <Button
                variant="glass"
                size="sm"
                onClick={() => setShowHistory(!showHistory)}
                className="w-full justify-between hover:bg-white/40"
              >
                <span className="flex items-center gap-2">
                  <History className="h-4 w-4" />
                  История запросов ({history.length})
                </span>
                {showHistory ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </Button>

              {showHistory && (
                <div className="grid gap-2 max-h-[300px] overflow-y-auto p-1 animate-in slide-in-from-top-2 scrollbar-none">
                  {history.map(h => (
                    <div
                      key={h.id}
                      onClick={() => handleActivateHistory(h)}
                      className={cn(
                        "p-3 rounded-lg border cursor-pointer transition-all backdrop-blur-main",
                        h.is_active 
                          ? "light-glass-primary text-white"
                          : "light-glass text-white"
                      )}
                    >
                      <div className={cn("font-medium")}>
                        {h.problem_text}
                      </div>
                      <div className="flex items-center gap-2 mt-1 text-xs text-white/60">
                        <span>{new Date(h.created_at).toLocaleDateString()}</span>
                        {h.is_active && <span className="text-white font-medium">• Активна</span>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {error && (
            <div className="p-4 rounded-lg bg-destructive/10 text-destructive text-sm font-medium border border-destructive/20 flex items-start gap-3">
              <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
              {error}
            </div>
          )}

          {success && (
            <div className="p-4 rounded-lg bg-green-50 text-green-700 text-sm font-medium border border-green-200 flex items-start gap-3">
              <CheckCircle2 className="h-5 w-5 shrink-0 mt-0.5" />
              {success}
            </div>
          )}

          {result && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">

              {/* MAIN CTA: ACTIVATE PROJECT */}
              <Card className="bg-white">
                <CardHeader>
                  <CardTitle className="text-primary flex items-center gap-2">
                    <Sparkles className="h-5 w-5" />
                    Решение найдено!
                  </CardTitle>
                  <CardDescription className="text-primary">
                    Хочешь, чтобы я провел тебя через 30-дневный путь исправления этой ситуации? 
                    Я буду давать тебе задания каждый день и поддерживать тебя.
                  </CardDescription>
                </CardHeader>
                <CardFooter>
                  <Button 
                    onClick={handleStartProject}
                    disabled={loading}
                    className="w-full text-white shadow-lg shadow-primary-200"
                    size="lg"
                  >
                    {loading ? 'Создаю проект...' : 'Начать Кармический Проект'}
                    <ArrowRight className="ml-2 h-5 w-5" />
                  </Button>
                </CardFooter>
              </Card>

              {/* Section: Diagnostics */}
              <Card className="text-white">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Search className="h-5 w-5 text-white" />
                    Диагностика
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider mb-2">Корень проблемы</h4>
                    <p className="font-medium">{result.root_cause}</p>
                  </div>

                  {result.imprint_logic && (
                    <div>
                      <h4 className="text-xs font-bold uppercase tracking-wider mb-2">Механизм отпечатка</h4>
                      <p className="text-sm leading-relaxed">{result.imprint_logic}</p>
                    </div>
                  )}

                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider mb-3">С кем практиковать (Партнеры)</h4>
                    <div className="flex flex-wrap gap-2">
                      {partners.length === 0 && (
                        <span className="text-sm italic">У тебя пока нет партнеров</span>
                      )}
                      {partners.map((p: any) => (
                        <button
                          key={p.id}
                          onClick={() => togglePartner(p.id)}
                          className={cn(
                            "px-3 py-1.5 rounded-full text-xs font-medium border transition-all",
                            selectedPartners.includes(p.id)
                              ? "bg-primary text-primary-foreground border-primary"
                              : "bg-secondary/50 text-secondary-foreground border-transparent hover:bg-secondary"
                          )}
                        >
                          {p.name}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="pt-2">
                    <Button onClick={handleStartPractice} className="w-full">
                      <Brain className="mr-2 h-4 w-4" />
                      В журнал
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Section: Action Plan STOP-START-GROW */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold px-1 text-white">🚀 План действий</h3>

                <Card className="border-l-4 border-l-red-500 text-white">
                  <CardContent className="p-4">
                    <h4 className="text-sm font-bold text-red-400 flex items-center gap-2 mb-1">
                      <AlertCircle className="h-4 w-4" /> STOP: Что прекратить
                    </h4>
                    <p className="text-sm">{result.stop_action}</p>
                  </CardContent>
                </Card>

                <Card className="border-l-4 border-l-green-500 text-white">
                  <CardContent className="p-4">
                    <h4 className="text-sm font-bold text-green-400 flex items-center gap-2 mb-1">
                      <CheckCircle2 className="h-4 w-4" /> START: Что начать
                    </h4>
                    <p className="text-sm">{result.start_action}</p>
                  </CardContent>
                </Card>

                <Card className="border-l-4 border-l-blue-500 text-white">
                  <CardContent className="p-4">
                    <h4 className="text-sm font-bold text-blue-400 flex items-center gap-2 mb-1">
                      <Target className="h-4 w-4" /> GROW: Как поливать
                    </h4>
                    <p className="text-sm">{result.grow_action}</p>
                  </CardContent>
                </Card>
              </div>

				{/* Section: Detailed Steps */}
				{result.practice_steps.length > 0 && (
					<Card className="text-white">
						<CardHeader className="flex flex-row items-center justify-between pb-2">
							<CardTitle className="text-lg">📅 План на 30 дней</CardTitle>
							<Button
								variant="ghost"
								size="sm"
								className="h-8"
								onClick={handleAddToCalendar}
								disabled={loading}
							>
								<Calendar className="mr-2 h-4 w-4"/>
								В календарь
							</Button>
						</CardHeader>
						<CardContent className="grid gap-4 pt-2">
							{result.practice_steps.map((step: string, i: number) => (
								<div key={i} className="flex gap-3 text-sm">
									<div
										className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold">
										{i + 1}
									</div>
									<p className="leading-relaxed pt-0.5">{step}</p>
								</div>
							))}
						</CardContent>
					</Card>
				)}

              {/* Section: Outcome & Tips */}
              <div className="grid gap-4 sm:grid-cols-2">
                {result.expected_outcome && (
                  <Card className="bg-secondary/20 border-none">
                    <CardContent className="p-4">
                      <h4 className="text-xs font-bold uppercase tracking-wider mb-2">Ожидаемый результат</h4>
                      <p className="text-sm font-medium">{result.expected_outcome}</p>
                    </CardContent>
                  </Card>
                )}
                {result.success_tip && (
                  <Card className="bg-amber-50 border-amber-100">
                    <CardContent className="p-4">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-amber-600 mb-2 flex items-center gap-1.5">
                        <Lightbulb className="h-3 w-3" /> Совет мастера
                      </h4>
                      <p className="text-sm text-amber-900">{result.success_tip}</p>
                    </CardContent>
                  </Card>
                )}
              </div>

              {/* Section: Key rule && practice */}
              {(result.rules?.length > 0 || result.practices?.length > 0) && (
                <div className="grid gap-4 sm:grid-cols-2">
                  {result.rules?.[0] && (
                    <Card>
                      <CardContent className="p-4">
                        <h4 className="text-xs font-bold uppercase tracking-wider mb-3">📜 Правило</h4>
                        <div className="space-y-1">
                          {result.rules[0].title && (
                            <div className="font-semibold text-sm">{result.rules[0].title}</div>
                          )}
                          {result.rules[0].number && (
                            <div className="text-xs">№ {result.rules[0].number}</div>
                          )}
                          <div className="text-sm mt-2">
                            {renderContent((result.rules[0].content || '').slice(0, 400))}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {result.practices?.[0] && (
                    <Card>
                      <CardContent className="p-4">
                        <h4 className="text-xs font-bold uppercase tracking-wider mb-3">🧘 Практика дня</h4>
                        <div className="space-y-1">
                          {(result.practices[0].name || result.practices[0].title) && (
                            <div className="font-semibold text-sm">{result.practices[0].name || result.practices[0].title}</div>
                          )}
                          {result.practices[0].duration && (
                            <div className="text-xs">{result.practices[0].duration} мин</div>
                          )}
                          <div className="text-sm mt-2">
                            {renderContent((result.practices[0].content || '').slice(0, 400))}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </div>
              )}

              {/* Section: Concepts from RAG */}
              {/*{result.concepts?.length > 0 && (*/}
              {/*  <div className="space-y-3">*/}
              {/*    <h3 className="text-sm font-semibold  px-1 uppercase tracking-wider">📖 Полезные концепции</h3>*/}
              {/*    <div className="grid gap-3">*/}
              {/*      {result.concepts.map((concept: any, i: number) => (*/}
              {/*        <Card key={i}>*/}
              {/*           <CardHeader className="py-3">*/}
              {/*             <CardTitle className="text-sm font-medium">{concept.title}</CardTitle>*/}
              {/*           </CardHeader>*/}
              {/*           <CardContent className="pb-3 pt-0 text-sm ">*/}
              {/*             {renderContent(concept.content)}*/}
              {/*           </CardContent>*/}
              {/*        </Card>*/}
              {/*      ))}*/}
              {/*    </div>*/}
              {/*  </div>*/}
              {/*)}*/}

              <div className="text-center text-xs text-white/50 pb-4">
                {result.timeline_days ? `Оценка времени проявления: ~${result.timeline_days} дней` : ''}
              </div>

            </div>
          )}
        </>
      )}
    </div>
  )
}

