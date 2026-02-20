import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getHabits, getPractices } from '../api/client'
import { Brain, CalendarDays, Clock, Dumbbell, Flame, Loader2, RefreshCw, Repeat, Play } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

interface PracticeItem {
  name: string
  category: string
  content: string
  duration: number
  score?: number
}

interface HabitItem {
  id: string
  practice_id: string
  frequency: string
  preferred_time: string
  duration: number
  is_active: boolean
}

export default function Practices() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [practices, setPractices] = useState<PracticeItem[]>([])
  const [habits, setHabits] = useState<HabitItem[]>([])
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    try {
      setError(null)
      setLoading(true)

      const [practicesData, habitsData] = await Promise.all([
        getPractices(),
        getHabits()
      ])

      setPractices(practicesData.practices || [])
      setHabits(habitsData.habits || [])
    } catch (e: any) {
      setError(e?.message || 'Failed to load practices')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  if (loading && practices.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-muted-foreground text-sm">Загружаем практики...</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6 p-4 max-w-5xl mx-auto w-full pb-24">
      <div className="space-y-1 mt-2 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-3">
            <Brain className="h-8 w-8 text-primary" />
            Практики
          </h1>
          <p className="text-muted-foreground leading-relaxed text-sm mt-1">
            Инструменты для работы с умом и кармой
          </p>
        </div>
        <Button variant="ghost" size="icon" onClick={load} disabled={loading}>
          <RefreshCw className={cn("h-5 w-5", loading && "animate-spin")} />
        </Button>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm font-medium border border-destructive/20">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Habits Section */}
        <div className="space-y-4">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Repeat className="h-5 w-5 text-muted-foreground" />
            Мои привычки
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
            {habits.length === 0 && (
              <div className="text-center py-8 text-muted-foreground bg-secondary/20 rounded-xl border border-dashed border-secondary text-sm col-span-full">
                Пока нет активных привычек
              </div>
            )}
            {habits.map((h) => (
              <Card key={h.id} className="border-none shadow-sm bg-gradient-to-r from-blue-50 to-indigo-50 border-l-4 border-l-blue-500">
                <CardContent className="p-4 flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-foreground flex items-center gap-2">
                      {h.practice_id}
                      {h.is_active && <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />}
                    </div>
                    <div className="flex flex-wrap gap-2 mt-2 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1 bg-white/50 px-2 py-1 rounded">
                        <CalendarDays className="h-3 w-3" />
                        {h.frequency}
                      </span>
                      <span className="flex items-center gap-1 bg-white/50 px-2 py-1 rounded">
                        <Clock className="h-3 w-3" />
                        {h.preferred_time}
                      </span>
                      <span className="flex items-center gap-1 bg-white/50 px-2 py-1 rounded">
                        <Dumbbell className="h-3 w-3" />
                        {h.duration} мин
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* Recommendations Section */}
        <div className="space-y-4">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Flame className="h-5 w-5 text-muted-foreground" />
            Рекомендации
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
            {practices.length === 0 && (
              <div className="text-center py-8 text-muted-foreground text-sm col-span-full">
                Пока нет рекомендаций
              </div>
            )}
            {practices.map((p, idx) => (
              <Card key={`${p.name}-${idx}`} className="overflow-hidden">
                <CardHeader className="bg-secondary/30 pb-3 pt-4">
                  <div className="flex justify-between items-start">
                    <CardTitle className="text-base font-semibold">{p.name}</CardTitle>
                    <div className="px-2 py-0.5 rounded-full bg-primary/10 text-primary text-[10px] font-bold uppercase tracking-wider">
                      {p.category}
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="p-4 pt-3">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground mb-3">
                    <Clock className="h-3 w-3" />
                    <span>{p.duration} мин</span>
                  </div>
                  <div className="text-sm text-foreground/90 whitespace-pre-wrap leading-relaxed mb-4">
                    {p.content}
                  </div>
                  <Button 
                    className="w-full" 
                    size="sm"
                    onClick={() => navigate(`/journal?description=${encodeURIComponent('Практика: ' + p.name)}&action_type=effort`)}
                  >
                    <Play className="h-3.5 w-3.5 mr-2" />
                    Начать выполнение
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
