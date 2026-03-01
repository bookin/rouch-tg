import { useEffect, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { getMergePreview, confirmMerge, type MergePreviewData } from '../api/client'
import { Loader2, CheckCircle2, AlertTriangle, Shield, ArrowDown } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function MergeAccounts() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const sourceId = Number(searchParams.get('source'))

  const [loading, setLoading] = useState(true)
  const [preview, setPreview] = useState<MergePreviewData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [merging, setMerging] = useState(false)
  const [done, setDone] = useState(false)
  const [keepFrom, setKeepFrom] = useState<number | null>(null)
  const [confirmed, setConfirmed] = useState(false)

  useEffect(() => {
    if (!sourceId) {
      setError('Не указан аккаунт для объединения')
      setLoading(false)
      return
    }
    getMergePreview(sourceId)
      .then(setPreview)
      .catch(() => setError('Не удалось загрузить данные для объединения'))
      .finally(() => setLoading(false))
  }, [sourceId])

  const handleMerge = async () => {
    if (!sourceId || !confirmed) return
    setMerging(true)
    setError(null)
    try {
      await confirmMerge(sourceId, keepFrom ?? undefined)
      setDone(true)
    } catch {
      setError('Ошибка при объединении. Попробуй позже.')
    } finally {
      setMerging(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  if (done) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="w-full max-w-sm text-center space-y-4 animate-in fade-in duration-500">
          <div className="relative mx-auto w-16 h-16">
            <CheckCircle2 className="w-16 h-16 text-emerald-400 animate-in zoom-in duration-300" />
          </div>
          <h1 className="text-xl font-semibold">Аккаунты объединены 🎉</h1>
          <p className="text-sm text-muted-foreground">
            Все данные теперь в одном месте. Можешь продолжить свой путь!
          </p>
          <Button onClick={() => navigate('/')} className="w-full">
            Перейти в приложение
          </Button>
        </div>
      </div>
    )
  }

  if (merging) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="w-full max-w-sm text-center space-y-6">
          <div className="relative mx-auto w-20 h-20">
            <div className="absolute inset-0 rounded-full border-2 border-primary/30 animate-ping" />
            <div className="absolute inset-2 rounded-full border-2 border-primary/50 animate-pulse" />
            <div className="absolute inset-0 flex items-center justify-center">
              <Loader2 className="w-10 h-10 animate-spin text-primary" />
            </div>
          </div>
          <div className="space-y-2">
            <h1 className="text-lg font-semibold">Объединяем аккаунты...</h1>
            <p className="text-sm text-muted-foreground">
              Переносим данные и настройки. Это займёт несколько секунд.
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (error && !preview) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="w-full max-w-sm text-center space-y-4">
          <AlertTriangle className="w-10 h-10 mx-auto text-amber-400" />
          <p className="text-sm text-muted-foreground">{error}</p>
          <Button variant="outline" onClick={() => navigate('/')}>На главную</Button>
        </div>
      </div>
    )
  }

  if (!preview) return null

  const { target, source, has_project_conflict } = preview
  const totalData = {
    seeds: target.seeds_count + source.seeds_count,
    partners: target.partners_count + source.partners_count,
    practices: target.practices_count + source.practices_count,
    plans: target.karma_plans_count + source.karma_plans_count,
    coffee: target.coffee_sessions_count + source.coffee_sessions_count,
  }

  return (
    <div className="max-w-lg mx-auto space-y-5 p-4 pb-24">
      <div className="text-center space-y-2">
        <div className="text-4xl">🔗</div>
        <h1 className="text-xl font-semibold">Объединение аккаунтов</h1>
        <p className="text-sm text-muted-foreground">
          Два аккаунта станут одним — все данные сольются вместе
        </p>
      </div>

      {/* Two account cards with arrow */}
      <div className="grid gap-2">
        <AccountCard label="Твой аккаунт (останется)" data={target} accent="emerald" />
        <div className="flex justify-center">
          <ArrowDown className="w-5 h-5 text-muted-foreground" />
        </div>
        <AccountCard label="Будет слит в основной" data={source} accent="amber" />
      </div>

      {/* What will be transferred */}
      <section className="rounded-xl bg-card/50 border border-border/50 p-4 space-y-3">
        <h3 className="text-sm font-medium">Что окажется в объединённом аккаунте:</h3>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <DataRow icon="🌱" label="Семян" value={totalData.seeds} />
          <DataRow icon="👥" label="Партнёров" value={totalData.partners} />
          <DataRow icon="🏆" label="Практик" value={totalData.practices} />
          <DataRow icon="📋" label="Проектов" value={totalData.plans} />
          <DataRow icon="☕" label="Медитаций" value={totalData.coffee} />
          {target.telegram_id || source.telegram_id ? (
            <DataRow icon="💬" label="Telegram" value="привязан" />
          ) : null}
        </div>
        {(target.email || source.email) && (
          <p className="text-xs text-muted-foreground">
            Email: <strong>{target.email || source.email}</strong>
          </p>
        )}
      </section>

      {/* Project conflict resolution */}
      {has_project_conflict && (
        <section className="rounded-xl bg-amber-900/20 border border-amber-600/30 p-4 space-y-3">
          <h3 className="text-sm font-medium flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            Оба аккаунта имеют активный проект
          </h3>
          <p className="text-xs text-muted-foreground">
            Выбери, какой проект оставить активным. Второй будет приостановлен — его можно будет возобновить позже.
          </p>
          <div className="space-y-2">
            <label className="flex items-start gap-2 cursor-pointer rounded-lg p-2 hover:bg-white/5 transition-colors">
              <input
                type="radio"
                name="keepProject"
                checked={keepFrom === target.id || keepFrom === null}
                onChange={() => setKeepFrom(target.id)}
                className="mt-1 accent-emerald-500"
              />
              <div>
                <p className="text-sm font-medium">Из основного аккаунта</p>
                {target.active_project_problem && (
                  <p className="text-xs text-muted-foreground">{target.active_project_problem}</p>
                )}
              </div>
            </label>
            <label className="flex items-start gap-2 cursor-pointer rounded-lg p-2 hover:bg-white/5 transition-colors">
              <input
                type="radio"
                name="keepProject"
                checked={keepFrom === source.id}
                onChange={() => setKeepFrom(source.id)}
                className="mt-1 accent-amber-500"
              />
              <div>
                <p className="text-sm font-medium">Из второго аккаунта</p>
                {source.active_project_problem && (
                  <p className="text-xs text-muted-foreground">{source.active_project_problem}</p>
                )}
              </div>
            </label>
          </div>
        </section>
      )}

      {/* Irreversibility warning + confirm checkbox */}
      <section className="rounded-xl bg-red-900/10 border border-red-600/20 p-4 space-y-3">
        <div className="flex items-start gap-2">
          <Shield className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
          <div className="space-y-1">
            <p className="text-sm font-medium text-red-300">Это действие необратимо</p>
            <p className="text-xs text-muted-foreground">
              Второй аккаунт будет удалён после переноса данных. Отменить объединение нельзя.
            </p>
          </div>
        </div>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={confirmed}
            onChange={(e) => setConfirmed(e.target.checked)}
            className="rounded accent-primary"
          />
          <span className="text-xs text-muted-foreground">
            Понимаю — хочу объединить аккаунты
          </span>
        </label>
      </section>

      {error && (
        <p className="text-sm text-red-400 bg-red-900/20 rounded-lg px-3 py-2">{error}</p>
      )}

      <Button onClick={handleMerge} disabled={!confirmed} className="w-full">
        Объединить аккаунты
      </Button>

      <button
        type="button"
        className="block w-full text-center text-sm text-muted-foreground hover:text-foreground transition-colors"
        onClick={() => navigate('/')}
      >
        Отмена — решу позже
      </button>
    </div>
  )
}

function DataRow({ icon, label, value }: { icon: string; label: string; value: number | string }) {
  return (
    <div className="flex items-center gap-1.5 text-muted-foreground">
      <span>{icon}</span>
      <span>{label}:</span>
      <span className="font-medium text-foreground">{value}</span>
    </div>
  )
}

function AccountCard({
  label,
  data,
  accent,
}: {
  label: string
  data: MergePreviewData['target']
  accent: 'emerald' | 'amber'
}) {
  const borderColor = accent === 'emerald' ? 'border-emerald-600/30' : 'border-amber-600/30'
  const bgColor = accent === 'emerald' ? 'bg-emerald-900/10' : 'bg-amber-900/10'
  return (
    <div className={`rounded-xl ${bgColor} border ${borderColor} p-4 space-y-2`}>
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{label}</p>
      <p className="text-sm font-medium">{data.first_name || 'Без имени'}</p>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
        {data.email && <span>📧 {data.email}</span>}
        {data.telegram_id && <span>💬 Telegram</span>}
        <span>🌱 {data.seeds_count}</span>
        <span>👥 {data.partners_count}</span>
        <span>🏆 {data.practices_count}</span>
        <span>📋 {data.karma_plans_count}</span>
      </div>
    </div>
  )
}
