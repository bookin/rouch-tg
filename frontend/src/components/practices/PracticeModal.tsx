import {X, Clock} from 'lucide-react'
import {Button} from '@/components/ui/button'
import type {PracticeDetails} from '@/components/practices/practiceUtils'
import {cn} from '@/lib/utils'

export type PracticeModalMode = 'details' | 'execute'

interface PracticeModalProps {
  open: boolean
  mode: PracticeModalMode
  practice: PracticeDetails | null
  onClose: () => void
  onStart?: (practiceId: string) => void
  onComplete?: (practiceId: string) => void
  isLoading?: boolean
}

const buildSteps = (steps?: string[]) => {
  if (!steps || steps.length === 0) {
    return ['Шаги пока не указаны. Сделай практику мягко и осознанно.']
  }

  return steps
}

export default function PracticeModal({
  open,
  mode,
  practice,
  onClose,
  onStart,
  onComplete,
  isLoading
}: PracticeModalProps) {
  if (!open || !practice) {
    return null
  }

  const steps = buildSteps(practice.steps)
  const showDetails = mode === 'details'

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 px-4">
      <div className="relative w-full max-w-xl rounded-3xl border border-white/20 bg-zinc-950/90 p-6 text-white shadow-xl backdrop-blur-xl">
        <button
          className="absolute right-4 top-4 text-white/50 transition hover:text-white"
          onClick={onClose}
          aria-label="Закрыть"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            {practice.category && (
              <span className="text-[10px] uppercase tracking-wider px-2 py-1 rounded bg-white/10 text-white/60">
                {practice.category}
              </span>
            )}
            {practice.duration ? (
              <span className="flex items-center gap-1 text-xs text-white/70">
                <Clock className="h-3.5 w-3.5" /> {practice.duration} мин
              </span>
            ) : null}
          </div>
          <h3 className="text-xl font-semibold">{practice.name}</h3>
          {practice.description && showDetails && (
            <p className="text-sm text-white/70">{practice.description}</p>
          )}
        </div>

        <div className="mt-5 space-y-4">
          <div>
            <p className="text-xs uppercase tracking-wider text-white/50 mb-2">Что делать</p>
            <ol className="space-y-2 text-sm">
              {steps.map((step, index) => (
                <li key={`${practice.id}-step-${index}`} className="flex gap-2">
                  <span className="text-white/40">{index + 1}.</span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>
          </div>

          {showDetails && practice.benefits && (
            <div>
              <p className="text-xs uppercase tracking-wider text-white/50 mb-2">Польза</p>
              <p className="text-sm text-white/70">{practice.benefits}</p>
            </div>
          )}

          {showDetails && practice.contraindications && practice.contraindications.length > 0 && (
            <div className="rounded-2xl border border-orange-400/20 bg-orange-500/10 p-4">
              <p className="text-xs uppercase tracking-wider text-orange-200 mb-2">Если есть ограничения</p>
              <p className="text-sm text-orange-100/90">
                {practice.contraindications.join(', ')}
              </p>
            </div>
          )}

          {showDetails && practice.tags && practice.tags.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {practice.tags.map((tag) => (
                <span key={`${practice.id}-tag-${tag}`} className="text-[10px] px-2 py-1 rounded bg-white/10 text-white/50">
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className={cn('mt-6 flex flex-col gap-3 sm:flex-row sm:items-center', showDetails ? 'sm:justify-between' : 'sm:justify-end')}>
          {showDetails ? (
            <Button
              className="w-full sm:w-auto"
              onClick={() => onStart?.(practice.id)}
              disabled={isLoading}
            >
              {isLoading ? 'Запускаю...' : 'Начать практику'}
            </Button>
          ) : (
            <Button
              className="w-full sm:w-auto"
              onClick={() => onComplete?.(practice.id)}
              disabled={isLoading}
            >
              {isLoading ? 'Отмечаю...' : 'Выполнено'}
            </Button>
          )}
          <Button
            variant={showDetails ? 'outline' : 'secondary'}
            className="w-full sm:w-auto"
            onClick={onClose}
          >
            {showDetails ? 'Закрыть' : 'Отложить'}
          </Button>
        </div>
      </div>
    </div>
  )
}
