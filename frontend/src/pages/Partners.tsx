import { FormEvent, useEffect, useMemo, useState } from 'react'
import { createPartner, getPartners, PartnerCreatePayload } from '../api/client'

interface PartnerGroup {
  id: string
  name: string
  icon: string
  description: string
  is_default: boolean
}

interface Partner {
  id: string
  name: string
  group_id: string
  telegram_username?: string
  phone?: string
  notes?: string
}

export default function Partners() {
  const [loading, setLoading] = useState(true)
  const [groups, setGroups] = useState<PartnerGroup[]>([])
  const [partners, setPartners] = useState<Partner[]>([])
  const [error, setError] = useState<string | null>(null)

  const [newPartnerName, setNewPartnerName] = useState('')
  const [newPartnerGroupId, setNewPartnerGroupId] = useState<string>('')
  const [newPartnerNotes, setNewPartnerNotes] = useState('')

  const groupById = useMemo(() => {
    const map = new Map<string, PartnerGroup>()
    groups.forEach((g) => map.set(g.id, g))
    return map
  }, [groups])

  const load = async () => {
    try {
      setError(null)
      setLoading(true)
      const data = await getPartners()
      setGroups(data.groups || [])
      setPartners(data.partners || [])
      if ((data.groups || []).length > 0 && !newPartnerGroupId) {
        setNewPartnerGroupId(data.groups[0].id)
      }
    } catch (e: any) {
      setError(e?.message || 'Failed to load partners')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const onCreatePartner = async (e: FormEvent) => {
    e.preventDefault()
    if (!newPartnerName.trim() || !newPartnerGroupId) return

    const payload: PartnerCreatePayload = {
      name: newPartnerName.trim(),
      group_id: newPartnerGroupId,
      notes: newPartnerNotes.trim() || undefined
    }

    try {
      setError(null)
      await createPartner(payload)
      setNewPartnerName('')
      setNewPartnerNotes('')
      await load()
    } catch (err: any) {
      setError(err?.message || 'Failed to create partner')
    }
  }

  if (loading) {
    return <div className="page">Загрузка...</div>
  }

  return (
    <div className="page">
      <h1>👥 Партнёры</h1>

      {error && (
        <div style={{ marginTop: 12, color: 'crimson' }}>
          {error}
        </div>
      )}

      <h2 style={{ marginTop: 16 }}>Группы</h2>
      <div style={{ display: 'grid', gap: 8, marginTop: 8 }}>
        {groups.map((g) => (
          <div
            key={g.id}
            style={{
              background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)',
              borderRadius: 10,
              padding: 12
            }}
          >
            <div style={{ fontWeight: 700 }}>
              {g.icon} {g.name}
            </div>
            <div style={{ opacity: 0.7, marginTop: 4 }}>
              {g.description}
            </div>
          </div>
        ))}
      </div>

      <h2 style={{ marginTop: 16 }}>Добавить партнёра</h2>
      <form onSubmit={onCreatePartner} style={{ display: 'grid', gap: 8, marginTop: 8 }}>
        <input
          value={newPartnerName}
          onChange={(e) => setNewPartnerName(e.target.value)}
          placeholder="Имя партнёра"
          style={{
            padding: 10,
            borderRadius: 8,
            border: '1px solid var(--tg-theme-hint-color, #ccc)',
            background: 'var(--tg-theme-bg-color, #fff)',
            color: 'var(--tg-theme-text-color, #000)'
          }}
        />
        <select
          value={newPartnerGroupId}
          onChange={(e) => setNewPartnerGroupId(e.target.value)}
          style={{
            padding: 10,
            borderRadius: 8,
            border: '1px solid var(--tg-theme-hint-color, #ccc)',
            background: 'var(--tg-theme-bg-color, #fff)',
            color: 'var(--tg-theme-text-color, #000)'
          }}
        >
          {groups.map((g) => (
            <option key={g.id} value={g.id}>
              {g.icon} {g.name}
            </option>
          ))}
        </select>
        <textarea
          value={newPartnerNotes}
          onChange={(e) => setNewPartnerNotes(e.target.value)}
          placeholder="Заметки (опционально)"
          rows={3}
          style={{
            padding: 10,
            borderRadius: 8,
            border: '1px solid var(--tg-theme-hint-color, #ccc)',
            background: 'var(--tg-theme-bg-color, #fff)',
            color: 'var(--tg-theme-text-color, #000)'
          }}
        />
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
          Добавить
        </button>
      </form>

      <h2 style={{ marginTop: 16 }}>Список</h2>
      <div style={{ display: 'grid', gap: 8, marginTop: 8 }}>
        {partners.length === 0 && (
          <div style={{ opacity: 0.7 }}>Пока нет партнёров</div>
        )}
        {partners.map((p) => {
          const group = groupById.get(p.group_id)
          return (
            <div
              key={p.id}
              style={{
                background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)',
                borderRadius: 10,
                padding: 12
              }}
            >
              <div style={{ fontWeight: 700 }}>{p.name}</div>
              <div style={{ opacity: 0.7, marginTop: 4 }}>
                {group ? `${group.icon} ${group.name}` : `Group: ${p.group_id}`}
              </div>
              {p.notes && (
                <div style={{ marginTop: 6, opacity: 0.9 }}>{p.notes}</div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
