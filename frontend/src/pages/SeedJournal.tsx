import { FormEvent, useEffect, useState } from 'react'
import { createSeed, getSeeds, SeedCreatePayload } from '../api/client'

interface SeedItem {
  id: string
  timestamp: string
  action_type: string
  description: string
  partner_group: string
  intention_score: number
  emotion_level: number
  strength_multiplier: number
  estimated_maturation_days: number
}

export default function SeedJournal() {
  const [loading, setLoading] = useState(true)
  const [seeds, setSeeds] = useState<SeedItem[]>([])
  const [error, setError] = useState<string | null>(null)

  const [description, setDescription] = useState('')
  const [actionType, setActionType] = useState('kindness')
  const [partnerGroup, setPartnerGroup] = useState('world')
  const [intentionScore, setIntentionScore] = useState(7)
  const [emotionLevel, setEmotionLevel] = useState(7)
  const [understanding, setUnderstanding] = useState(true)

  const load = async () => {
    try {
      setError(null)
      setLoading(true)
      const data = await getSeeds(200)
      setSeeds(data.seeds || [])
    } catch (e: any) {
      setError(e?.message || 'Failed to load seeds')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const onCreate = async (e: FormEvent) => {
    e.preventDefault()
    if (!description.trim()) return

    const payload: SeedCreatePayload = {
      description: description.trim(),
      action_type: actionType,
      partner_group: partnerGroup,
      intention_score: intentionScore,
      emotion_level: emotionLevel,
      understanding,
      estimated_maturation_days: 21,
      strength_multiplier: 1.5
    }

    try {
      setError(null)
      await createSeed(payload)
      setDescription('')
      await load()
    } catch (err: any) {
      setError(err?.message || 'Failed to create seed')
    }
  }

  if (loading) {
    return <div className="page">Загрузка...</div>
  }

  return (
    <div className="page">
      <h1>🌱 Журнал семян</h1>

      {error && (
        <div style={{ marginTop: 12, color: 'crimson' }}>
          {error}
        </div>
      )}

      <h2 style={{ marginTop: 16 }}>Посадить семя</h2>
      <form onSubmit={onCreate} style={{ display: 'grid', gap: 8, marginTop: 8 }}>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Что ты сделал(а) для других?"
          rows={3}
          style={{
            padding: 10,
            borderRadius: 8,
            border: '1px solid var(--tg-theme-hint-color, #ccc)',
            background: 'var(--tg-theme-bg-color, #fff)',
            color: 'var(--tg-theme-text-color, #000)'
          }}
        />
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          <select
            value={actionType}
            onChange={(e) => setActionType(e.target.value)}
            style={{
              padding: 10,
              borderRadius: 8,
              border: '1px solid var(--tg-theme-hint-color, #ccc)',
              background: 'var(--tg-theme-bg-color, #fff)'
            }}
          >
            <option value="giving">Даяние</option>
            <option value="kindness">Доброта</option>
            <option value="patience">Терпение</option>
            <option value="effort">Усилие</option>
            <option value="concentration">Сосредоточение</option>
            <option value="wisdom">Мудрость</option>
          </select>
          <select
            value={partnerGroup}
            onChange={(e) => setPartnerGroup(e.target.value)}
            style={{
              padding: 10,
              borderRadius: 8,
              border: '1px solid var(--tg-theme-hint-color, #ccc)',
              background: 'var(--tg-theme-bg-color, #fff)'
            }}
          >
            <option value="colleagues">Коллеги</option>
            <option value="clients">Клиенты</option>
            <option value="suppliers">Поставщики</option>
            <option value="world">Мир</option>
          </select>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          <label style={{ display: 'grid', gap: 4 }}>
            <span style={{ fontSize: 12, opacity: 0.7 }}>Намерение (1-10)</span>
            <input
              type="number"
              min={1}
              max={10}
              value={intentionScore}
              onChange={(e) => setIntentionScore(Number(e.target.value))}
              style={{
                padding: 10,
                borderRadius: 8,
                border: '1px solid var(--tg-theme-hint-color, #ccc)',
                background: 'var(--tg-theme-bg-color, #fff)'
              }}
            />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span style={{ fontSize: 12, opacity: 0.7 }}>Эмоция (1-10)</span>
            <input
              type="number"
              min={1}
              max={10}
              value={emotionLevel}
              onChange={(e) => setEmotionLevel(Number(e.target.value))}
              style={{
                padding: 10,
                borderRadius: 8,
                border: '1px solid var(--tg-theme-hint-color, #ccc)',
                background: 'var(--tg-theme-bg-color, #fff)'
              }}
            />
          </label>
        </div>

        <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <input
            type="checkbox"
            checked={understanding}
            onChange={(e) => setUnderstanding(e.target.checked)}
          />
          <span>Делал(а) с пониманием механизма</span>
        </label>

        <button
          type="submit"
          style={{
            padding: 12,
            borderRadius: 10,
            border: 'none',
            background: 'var(--tg-theme-button-color, #3390ec)',
            color: 'var(--tg-theme-button-text-color, #fff)',
            fontWeight: 700
          }}
        >
          Посадить 🌱
        </button>
      </form>

      <h2 style={{ marginTop: 16 }}>История</h2>
      <div style={{ display: 'grid', gap: 8, marginTop: 8 }}>
        {seeds.length === 0 && (
          <div style={{ opacity: 0.7 }}>Пока нет семян</div>
        )}
        {seeds.map((s) => (
          <div
            key={s.id}
            style={{
              background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)',
              borderRadius: 10,
              padding: 12
            }}
          >
            <div style={{ fontWeight: 700 }}>🌱 {s.description}</div>
            <div style={{ opacity: 0.7, marginTop: 4 }}>
              {new Date(s.timestamp).toLocaleString()}
            </div>
            <div style={{ opacity: 0.7, marginTop: 4 }}>
              Тип: {s.action_type} · Группа: {s.partner_group}
            </div>
            <div style={{ opacity: 0.7, marginTop: 4 }}>
              Сила: {s.strength_multiplier}x · Созревание: {s.estimated_maturation_days}д
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
