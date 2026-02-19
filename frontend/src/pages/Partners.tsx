import { FormEvent, useEffect, useMemo, useState } from 'react'
import { createPartner, getPartners, PartnerCreatePayload } from '../api/client'

interface PartnerGroup {
  id: string
  name: string
  icon: string
  description: string
  universal_category?: string
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

const CATEGORY_LABELS: Record<string, string> = {
  source: 'Источник (Source)',
  ally: 'Соратник (Ally)',
  protege: 'Подопечный (Protege)',
  world: 'Внешний мир (World)'
}

const CATEGORY_DESCRIPTIONS: Record<string, string> = {
  source: 'Те, кто дает ресурсы (Родители, учителя, менторы)',
  ally: 'Те, кто помогает в делах (Коллеги, партнеры, супруги)',
  protege: 'Те, кто зависит от тебя (Клиенты, дети, подчиненные)',
  world: 'Далекие люди или конкуренты'
}

const CATEGORY_ORDER = ['source', 'ally', 'protege', 'world']

export default function Partners() {
  const [loading, setLoading] = useState(true)
  const [groups, setGroups] = useState<PartnerGroup[]>([])
  const [partners, setPartners] = useState<Partner[]>([])
  const [error, setError] = useState<string | null>(null)

  const [newPartnerName, setNewPartnerName] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('source')
  const [newPartnerNotes, setNewPartnerNotes] = useState('')

  const load = async () => {
    try {
      setError(null)
      setLoading(true)
      const data = await getPartners()
      setGroups(data.groups || [])
      setPartners(data.partners || [])
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

  // Helpers to resolve group from category
  const getGroupByCategory = (cat: string) => {
    return groups.find(g => g.universal_category === cat) || groups[0]
  }

  const partnersByCategory = useMemo(() => {
    const map: Record<string, Partner[]> = { source: [], ally: [], protege: [], world: [] }
    
    // Create lookup for group -> category
    const groupCatMap = new Map<string, string>()
    groups.forEach(g => {
      if (g.universal_category) groupCatMap.set(g.id, g.universal_category)
    })

    partners.forEach(p => {
      const cat = groupCatMap.get(p.group_id) || 'world'
      if (!map[cat]) map[cat] = []
      map[cat].push(p)
    })
    
    return map
  }, [groups, partners])

  const onCreatePartner = async (e: FormEvent) => {
    e.preventDefault()
    if (!newPartnerName.trim()) return

    const targetGroup = getGroupByCategory(selectedCategory)
    if (!targetGroup) {
      setError('Группа для этой категории не найдена')
      return
    }

    const payload: PartnerCreatePayload = {
      name: newPartnerName.trim(),
      group_id: targetGroup.id,
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
    <div className="page" style={{ paddingBottom: 80 }}>
      <h1>👥 Кармические Партнёры</h1>
      <p style={{ opacity: 0.7, fontSize: '0.9rem', marginBottom: 20 }}>
        Ваши партнеры — это почва, в которую вы сажаете семена для достижения своих целей.
      </p>

      {error && (
        <div style={{ marginTop: 12, color: 'crimson', background: '#fff0f0', padding: 10, borderRadius: 8 }}>
          {error}
        </div>
      )}

      {/* Partners List Grouped by Category */}
      <div style={{ display: 'grid', gap: 24 }}>
        {CATEGORY_ORDER.map(cat => {
          const catPartners = partnersByCategory[cat] || []
          const groupInfo = getGroupByCategory(cat)
          
          return (
            <div key={cat} style={{ background: '#fff', padding: 16, borderRadius: 16, border: '1px solid #eee' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <div style={{ fontSize: '1.5rem' }}>{groupInfo?.icon || '👤'}</div>
                <div>
                  <div style={{ fontWeight: 700, fontSize: '1rem' }}>{CATEGORY_LABELS[cat]}</div>
                  <div style={{ fontSize: '0.8rem', opacity: 0.6 }}>{CATEGORY_DESCRIPTIONS[cat]}</div>
                </div>
              </div>

              <div style={{ marginTop: 12, display: 'grid', gap: 8 }}>
                {catPartners.length === 0 && (
                  <div style={{ fontSize: '0.85rem', opacity: 0.5, fontStyle: 'italic', paddingLeft: 8 }}>
                    Пока никого нет
                  </div>
                )}
                {catPartners.map(p => (
                  <div key={p.id} style={{ 
                    background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)', 
                    padding: '10px 14px', 
                    borderRadius: 10,
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}>
                    <span style={{ fontWeight: 500 }}>{p.name}</span>
                    {p.notes && <span style={{ fontSize: '0.8rem', opacity: 0.5 }}>📝</span>}
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>

      {/* Add Partner Form */}
      <div style={{ marginTop: 30, background: '#f0f8ff', padding: 16, borderRadius: 16, border: '1px solid #d0e8ff' }}>
        <h3 style={{ margin: '0 0 12px 0', fontSize: '1.1rem', color: '#0056b3' }}>➕ Добавить партнёра</h3>
        <form onSubmit={onCreatePartner} style={{ display: 'grid', gap: 12 }}>
          
          <div>
            <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: 6, fontWeight: 500 }}>Категория</label>
            <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 4 }}>
              {CATEGORY_ORDER.map(cat => {
                const isActive = selectedCategory === cat
                const g = getGroupByCategory(cat)
                return (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => setSelectedCategory(cat)}
                    style={{
                      padding: '8px 12px',
                      borderRadius: 20,
                      border: isActive ? '1px solid #0056b3' : '1px solid #ddd',
                      background: isActive ? '#0056b3' : '#fff',
                      color: isActive ? '#fff' : '#333',
                      fontSize: '0.85rem',
                      whiteSpace: 'nowrap',
                      cursor: 'pointer'
                    }}
                  >
                    {g?.icon} {CATEGORY_LABELS[cat].split('(')[0]}
                  </button>
                )
              })}
            </div>
          </div>

          <input
            value={newPartnerName}
            onChange={(e) => setNewPartnerName(e.target.value)}
            placeholder="Имя партнёра"
            style={{
              padding: 12,
              borderRadius: 10,
              border: '1px solid #ccc',
              fontSize: '1rem',
              outline: 'none'
            }}
          />
          
          <textarea
            value={newPartnerNotes}
            onChange={(e) => setNewPartnerNotes(e.target.value)}
            placeholder="Заметки (что он любит, день рождения...)"
            rows={2}
            style={{
              padding: 12,
              borderRadius: 10,
              border: '1px solid #ccc',
              fontSize: '0.9rem',
              resize: 'none',
              outline: 'none',
              fontFamily: 'inherit'
            }}
          />

          <button
            type="submit"
            disabled={!newPartnerName.trim()}
            style={{
              padding: 14,
              borderRadius: 12,
              border: 'none',
              background: newPartnerName.trim() ? '#0056b3' : '#ccc',
              color: '#fff',
              fontWeight: 700,
              fontSize: '1rem',
              cursor: newPartnerName.trim() ? 'pointer' : 'not-allowed',
              transition: '0.2s'
            }}
          >
            Сохранить партнёра
          </button>
        </form>
      </div>
    </div>
  )
}
