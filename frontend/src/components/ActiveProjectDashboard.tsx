import { useState } from 'react'
import { ProjectStatusResponse, completeDailyProjectPlan } from '../api/client'
import { Calendar, Check, Coffee, Sprout, StopCircle, PlayCircle, Trophy, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Progress } from '@/components/ui/progress'

interface Props {
  data: ProjectStatusResponse
  onRefresh: () => void
}

const qualityRuMap: Record<string, string> = {
    'Giving': 'Щедрость',
    'Ethics': 'Этика',
    'Patience': 'Терпение',
    'Effort': 'Усилие',
    'Concentration': 'Сосредоточенность',
    'Wisdom': 'Мудрость',
    'Compassion': 'Сострадание',
}

export default function ActiveProjectDashboard({ data, onRefresh }: Props) {
  const { project, daily_plan } = data
  const [completedTasks, setCompletedTasks] = useState<string[]>([])
  const [notes, setNotes] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  if (!project) return null

  const handleTaskToggle = (taskId: string) => {
    if (daily_plan?.is_completed) return // Read only if already completed today

    setCompletedTasks((prev: string[]) => {
      if (prev.includes(taskId)) {
        return prev.filter((t: string) => t !== taskId)
      }
      return [...prev, taskId]
    })
  }

  const handleCompleteDay = async () => {
    if (!daily_plan) return
    
    try {
      setIsSubmitting(true)
      await completeDailyProjectPlan({
        plan_id: project.id,
        completed_tasks: completedTasks,
        notes: notes
      })
      onRefresh() // Refresh parent data
    } catch (e) {
      console.error('Failed to complete day', e)
      alert('Не удалось завершить день. Попробуй еще раз.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const progressPercent = Math.min(100, Math.round((project.day_number / project.duration_days) * 100))

  return (
    <div className="space-y-6">
      
      {/* Header Card */}
      <Card className="border-none shadow-lg bg-gradient-to-br from-green-700 to-primary text-white overflow-hidden relative">
        <div className="absolute top-0 right-0 p-8 opacity-10">
          <Trophy className="w-32 h-32" />
        </div>
        <CardContent className="p-6 relative z-10">
          <div className="flex justify-between items-start mb-4">
            <div>
              <div className="text-xs font-bold uppercase tracking-wider opacity-80 mb-1">
                Активный проект
              </div>
              <h2 className="text-xl font-bold leading-tight">
                {project.problem}
              </h2>
            </div>
            <div className="bg-white/20 backdrop-blur-md px-3 py-1 rounded-full text-xs font-bold whitespace-nowrap">
              День {project.day_number}/{project.duration_days}
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-xs opacity-90">
              <span>Прогресс</span>
              <span>{progressPercent}%</span>
            </div>
            <Progress value={progressPercent} className="h-2 bg-white/20" />
          </div>
        </CardContent>
      </Card>

      {/* Daily Plan Card */}
      {daily_plan ? (
        <Card>
          <CardHeader className="pb-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-white/60 border-white/20 flex items-center justify-center text-primary shadow-md">
                <Calendar className="h-5 w-5" />
              </div>
              <div>
                <CardTitle className="text-lg">План на сегодня</CardTitle>
                <p className="text-sm text-white/70">
                  Качество дня: <span className="font-bold">{qualityRuMap[daily_plan.focus_quality]}</span>
                </p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-3">
              {daily_plan.tasks.map((task) => {
                const isChecked =
                  daily_plan.is_completed || task.completed || completedTasks.includes(task.id)
                return (
                  <div 
                    key={task.id}
                    onClick={() => handleTaskToggle(task.id)}
                    className={cn(
                      "flex items-center gap-3 p-3 rounded-xl transition-all border cursor-pointer border-white/30",
                      isChecked 
                        ? "bg-white/20 text-white/50 decoration-muted-foreground/50"
                        : "bg-white/10 hover:bg-white/20",
                      daily_plan.is_completed && "cursor-default"
                    )}
                  >
                    <div className={cn(
                      "mt-0.5 h-6 w-6 rounded-md border flex items-center justify-center shrink-0 transition-colors",
                      isChecked 
                        ? "border-primary/80 bg-primary text-white"
                        : "border-white/50 "
                    )}>
                      {isChecked && <Check className="h-3.5 w-3.5" />}
                    </div>
                    <span className={cn(
                      "text-sm leading-relaxed",
                      isChecked && " line-through"
                    )}>
                      {task.description}
                    </span>
                  </div>
                )
              })}
            </div>

            {!daily_plan.is_completed && (
              <div className="space-y-4 pt-4 border-t">
                <Textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Заметки к кофе-медитации (как прошел день?)..."
                  className="min-h-[80px]"
                />
                
                <Button
                  onClick={handleCompleteDay}
                  disabled={isSubmitting || completedTasks.length === 0}
                  className="w-full font-bold"
                  size="lg"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Сохраняем...
                    </>
                  ) : (
                    <>
                      <Coffee className="mr-2 h-4 w-4" />
                      Завершить день
                    </>
                  )}
                </Button>
              </div>
            )}

            {daily_plan.is_completed && (
              <div className="bg-green-50 text-green-700 p-3 rounded-lg text-center text-sm font-medium flex items-center justify-center gap-2">
                <Sprout className="h-4 w-4" />
                ✨ День завершен! Ты молодец.
              </div>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card className="bg-white/10 border-dashed">
          <CardContent className="p-8 text-center ">
            <Calendar className="h-8 w-8 mx-auto mb-3 opacity-50" />
            <p>План на сегодня еще не сформирован.</p>
            <p className="text-xs mt-1">Загляни в утренние сообщения!</p>
          </CardContent>
        </Card>
      )}

      {/* Strategy Summary Card */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold uppercase tracking-wider  flex items-center gap-2">
            <Trophy className="h-4 w-4" />
            Стратегия успеха
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-3">
            <StopCircle className="h-5 w-5 text-orange-400 shrink-0" />
            <div className="space-y-1">
              <div className="text-xs font-bold text-orange-400">STOP</div>
              <div className="text-sm">{project.strategy.stop_action}</div>
            </div>
          </div>
          
          <div className="flex gap-3">
            <PlayCircle className="h-5 w-5 text-green-400 shrink-0" />
            <div className="space-y-1">
              <div className="text-xs font-bold text-green-400">START</div>
              <div className="text-sm">{project.strategy.start_action}</div>
            </div>
          </div>

          <div className="flex gap-3">
            <Sprout className="h-5 w-5 text-blue-400 shrink-0" />
            <div className="space-y-1">
              <div className="text-xs font-bold text-blue-400">GROW</div>
              <div className="text-sm">{project.strategy.grow_action}</div>
            </div>
          </div>
        </CardContent>
      </Card>
      
    </div>
  )
}
