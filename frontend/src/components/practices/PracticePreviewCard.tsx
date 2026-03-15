import {Clock} from 'lucide-react'
import {Card} from '@/components/ui/card'
import {cn} from '@/lib/utils'
import type {PracticeDetails} from '@/components/practices/practiceUtils'

interface PracticePreviewCardProps {
  practice: PracticeDetails
  onClick: () => void
  variant?: 'default' | 'highlight'
}

const variants = {
  default: 'border border-white/10 bg-white/5 hover:bg-white/10',
  highlight: 'border border-yellow-500/20 bg-yellow-500/5 hover:bg-yellow-500/10'
}

export default function PracticePreviewCard({practice, onClick, variant = 'default'}: PracticePreviewCardProps) {
  return (
    <Card
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          onClick()
        }
      }}
      className={cn(
        'group cursor-pointer rounded-2xl p-4 transition-all duration-300 backdrop-blur-main focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40',
        variants[variant]
      )}
    >
      <div className="flex items-start justify-between mb-2">
        <h3 className="font-semibold text-white text-sm">{practice.name}</h3>
        {practice.category && (
          <span className={cn(
            'text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded',
            variant === 'highlight' ? 'bg-yellow-500/20 text-yellow-300' : 'bg-white/10 text-white/40'
          )}>
            {practice.category}
          </span>
        )}
      </div>
      {practice.duration ? (
        <div className="flex items-center gap-2 text-xs text-white/60 mb-2">
          <Clock className="h-3 w-3" /> {practice.duration} мин
        </div>
      ) : null}
      {practice.benefits && (
        <p className="text-xs text-white/50 line-clamp-2">{practice.benefits}</p>
      )}
    </Card>
  )
}
