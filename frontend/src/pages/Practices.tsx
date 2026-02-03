import { useEffect, useState } from 'react'
import { getHabits, getPractices } from '../api/client'

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

  if (loading) {
    return <div className="page">Загрузка...</div>
  }

  return (
    <div className="page">
      <h1>🧘 Практики</h1>

      {error && (
        <div style={{ marginTop: 12, color: 'crimson' }}>
          {error}
        </div>
      )}

      <h2 style={{ marginTop: 16 }}>Рекомендации</h2>
      <div style={{ display: 'grid', gap: 8, marginTop: 8 }}>
        {practices.length === 0 && (
          <div style={{ opacity: 0.7 }}>Пока нет рекомендаций</div>
        )}
        {practices.map((p, idx) => (
          <div
            key={`${p.name}-${idx}`}
            style={{
              background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)',
              borderRadius: 10,
              padding: 12
            }}
          >
            <div style={{ fontWeight: 700 }}>{p.name}</div>
            <div style={{ opacity: 0.7, marginTop: 4 }}>
              Категория: {p.category} · Длительность: {p.duration} мин
            </div>
            <div style={{ marginTop: 8, whiteSpace: 'pre-wrap' }}>
              {p.content}
            </div>
          </div>
        ))}
      </div>

      <h2 style={{ marginTop: 16 }}>Привычки</h2>
      <div style={{ display: 'grid', gap: 8, marginTop: 8 }}>
        {habits.length === 0 && (
          <div style={{ opacity: 0.7 }}>Пока нет привычек</div>
        )}
        {habits.map((h) => (
          <div
            key={h.id}
            style={{
              background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)',
              borderRadius: 10,
              padding: 12
            }}
          >
            <div style={{ fontWeight: 700 }}>Habit: {h.practice_id}</div>
            <div style={{ opacity: 0.7, marginTop: 4 }}>
              {h.frequency} · {h.preferred_time} · {h.duration} мин · {h.is_active ? 'active' : 'paused'}
            </div>
          </div>
        ))}
      </div>

      <button
        onClick={load}
        style={{
          marginTop: 16,
          padding: 12,
          borderRadius: 10,
          border: 'none',
          background: 'var(--tg-theme-button-color, #3390ec)',
          color: 'var(--tg-theme-button-text-color, #fff)',
          fontWeight: 700
        }}
      >
        Обновить
      </button>
    </div>
  )
}
