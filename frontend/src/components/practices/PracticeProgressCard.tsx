import {Clock, Flame, Play, TrendingUp} from 'lucide-react'
import {Card} from '@/components/ui/card'
import {Button} from '@/components/ui/button'
import {cn} from '@/lib/utils'
import type {PracticeProgress} from '@/api/client'

interface PracticeProgressCardProps {
  practice: PracticeProgress
  isLoading?: boolean
  onExecute?: (practice: PracticeProgress) => void
  menu?: React.ReactNode
  showDuration?: boolean
}

export default function PracticeProgressCard({
  practice,
  isLoading = false,
  onExecute,
  menu,
  showDuration = true
}: PracticeProgressCardProps) {
  return (
    <Card
      className={cn(
        'group relative overflow-hidden rounded-2xl border p-4 transition-all duration-300 backdrop-blur-main',
        practice.is_habit
          ? 'bg-green-500/15 border-green-400/30'
          : !practice.is_active
          ? 'bg-white/5 border-white/10 opacity-60'
          : 'bg-white/10 border-white/20',
        isLoading && 'opacity-70 pointer-events-none'
      )}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <span className="text-lg">{practice.is_habit ? '🌿' : '🧘'}</span>
          <h3 className="font-semibold text-white text-sm truncate">{practice.practice_name}</h3>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-white/10 text-white/50">
            {practice.practice_category}
          </span>
          {menu}
        </div>
      </div>

      <div className="flex items-center gap-3 text-xs text-white/70 mb-2">
        {practice.streak_days > 0 && (
          <span className="flex items-center gap-1">
            <Flame className="h-3 w-3 text-orange-300" />
            {practice.streak_days} дн.
          </span>
        )}
        {practice.habit_score > 0 && (
          <span className="flex items-center gap-1">
            <TrendingUp className="h-3 w-3 text-blue-300" />
            {practice.habit_score}%
          </span>
        )}
        {showDuration && (
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {practice.practice_duration} мин
          </span>
        )}
      </div>

      {!practice.is_habit && practice.habit_score > 0 && (
        <div className="mb-3">
          <div className="w-full h-1.5 bg-white/20 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-400 to-green-400 transition-all duration-300"
              style={{width: `${Math.min(100, (practice.habit_score / practice.habit_min_score) * 100)}%`}}
            />
          </div>
          <p className="text-[10px] text-white/40 mt-1">
            До привычки: {practice.habit_score}/{practice.habit_min_score}% · {practice.streak_days}/{practice.habit_min_streak_days} дн.
          </p>
        </div>
      )}

      {practice.is_habit && (
        <p className="text-xs text-green-300 font-medium mb-2">✅ Сформированная привычка</p>
      )}

      {!practice.is_active && (
        <p className="text-xs text-yellow-300/70 font-medium mb-2">⏸ На паузе</p>
      )}

      {practice.is_active && practice.can_complete_today && !practice.is_habit && onExecute && (
        <Button size="sm" className="w-full mt-1" onClick={() => onExecute(practice)}>
          {isLoading ? <Play className="h-3.5 w-3.5 mr-2 animate-spin" /> : <Play className="h-3.5 w-3.5 mr-2" />}
          Выполнить
        </Button>
      )}
    </Card>
  )
}
