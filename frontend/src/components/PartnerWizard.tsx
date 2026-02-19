import { useState, useEffect, ChangeEvent } from 'react'
import { 
  getProjectSetup, 
  activateProject, 
  createPartner, 
  ProjectSetupResponse, 
  PartnerOut,
  ProjectStatusResponse
} from '../api/client'

interface Props {
  historyId: string
  onComplete: (projectData: ProjectStatusResponse) => void
  onCancel: () => void
}

type Step = 'intro' | 'source' | 'ally' | 'protege' | 'world' | 'finish'

export default function PartnerWizard({ historyId, onComplete, onCancel }: Props) {
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [setupData, setSetupData] = useState<ProjectSetupResponse | null>(null)
  const [step, setStep] = useState<Step>('intro')
  const [selections, setSelections] = useState<Record<string, string[]>>({
    source: [],
    ally: [],
    protege: [],
    world: []
  })
  
  const [isolationSettings, setIsolationSettings] = useState<Record<string, { is_isolated: boolean }>>({
    source: { is_isolated: false },
    ally: { is_isolated: false },
    protege: { is_isolated: false },
    world: { is_isolated: false }
  })

  // For creating new partner
  const [newPartnerName, setNewPartnerName] = useState('')
  const [newPartnerContactType, setNewPartnerContactType] = useState<'physical' | 'online'>('physical')
  const [isCreating, setIsCreating] = useState(false)

  useEffect(() => {
    loadSetup()
  }, [historyId])

  const loadSetup = async () => {
    try {
      setLoading(true)
      const data = await getProjectSetup(historyId)
      setSetupData(data)
    } catch (e) {
      console.error('Failed to load project setup', e)
      alert('Ошибка загрузки данных. Попробуйте позже.')
      onCancel()
    } finally {
      setLoading(false)
    }
  }

  const getGuide = (category: string) => {
    return setupData?.partner_selection_guide?.find((g: any) => g.category === category)
  }

  const handleNext = async () => {
    if (step === 'intro') setStep('source')
    else if (step === 'source') setStep('ally')
    else if (step === 'ally') setStep('protege')
    else if (step === 'protege') setStep('world')
    else if (step === 'world') {
      await finishSetup()
    }
  }

  const handleBack = () => {
    if (step === 'source') setStep('intro')
    else if (step === 'ally') setStep('source')
    else if (step === 'protege') setStep('ally')
    else if (step === 'world') setStep('protege')
  }

  const togglePartner = (category: string, id: string) => {
    setSelections((prev: Record<string, string[]>) => {
      const current = prev[category] || []
      const updated = current.includes(id) 
        ? current.filter((p: string) => p !== id)
        : [...current, id]
      
      return { ...prev, [category]: updated }
    })
  }

  const handleCreatePartner = async (category: string) => {
    if (!newPartnerName.trim()) return
    
    try {
      setIsCreating(true)
      // fetch partners to find group
      const partnersData = await import('../api/client').then(m => m.getPartners())
      const group = partnersData.groups.find((g: any) => g.universal_category === category)
      
      if (!group) {
        alert('Ошибка: группа для этой категории не найдена')
        return
      }

      const newP = await createPartner({
        name: newPartnerName,
        group_id: group.id,
        contact_type: newPartnerContactType
      })
      
      if (newP.success) {
        // Add to local state
        const p: PartnerOut = {
          id: newP.partner_id,
          name: newPartnerName,
          group_id: group.id,
          contact_type: newPartnerContactType
        }
        
        setSetupData((prev: ProjectSetupResponse | null) => {
          if (!prev) return null
          const catList = prev.user_partners[category] || []
          return {
            ...prev,
            user_partners: {
              ...prev.user_partners,
              [category]: [...catList, p]
            }
          }
        })
        
        // Auto select
        togglePartner(category, newP.partner_id)
        setNewPartnerName('')
        setNewPartnerContactType('physical')
      }
      
    } catch (e) {
      console.error(e)
      alert('Не удалось создать партнера')
    } finally {
      setIsCreating(false)
    }
  }

  const finishSetup = async () => {
    try {
      setSubmitting(true)
      const res = await activateProject({
        history_id: historyId,
        project_partners: selections,
        isolation_settings: isolationSettings
      })
      onComplete(res)
    } catch (e) {
      console.error(e)
      alert('Не удалось активировать проект')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading || !setupData) {
    return <div style={{ padding: 40, textAlign: 'center' }}>Загрузка мастера...</div>
  }

  if (step === 'intro') {
    return (
      <div style={{ padding: 20 }}>
        <h2>🌱 Почва для семян</h2>
        <p style={{ lineHeight: '1.5', opacity: 0.8 }}>
          Чтобы достичь цели <b>{setupData.problem}</b>, нам нужно посадить ментальные семена. 
          Семена нельзя посадить в пустоту — нужны другие люди.
        </p>
        <p style={{ lineHeight: '1.5', opacity: 0.8 }}>
          Сейчас мы выберем 4 кармических партнеров для этого проекта.
        </p>
        <div style={{ marginTop: 30, display: 'flex', gap: 10 }}>
          <button 
            onClick={onCancel}
            style={{ flex: 1, padding: 14, borderRadius: 12, border: 'none', background: '#eee', color: '#333', fontWeight: 600, cursor: 'pointer' }}
          >
            Отмена
          </button>
          <button 
            onClick={handleNext}
            style={{ flex: 2, padding: 14, borderRadius: 12, border: 'none', background: 'var(--tg-theme-button-color, #3390ec)', color: '#fff', fontWeight: 600, cursor: 'pointer' }}
          >
            Начать выбор
          </button>
        </div>
      </div>
    )
  }

  const renderStep = (category: string) => {
    const guide = getGuide(category)
    const partners = setupData.user_partners[category] || []
    const selected = selections[category] || []
    const isIsolated = isolationSettings[category]?.is_isolated || false

    // If no guide found (should not happen with backend fallback), show generic
    const displayTitle = guide?.title || category.toUpperCase()
    const displayDesc = guide?.description || 'Выберите партнера для этой категории'
    const fallbackAdvice = guide?.fallback_advice || 'Если нет партнера в этой категории, используйте ментальные семена.'

    const handleIsolationToggle = (e: ChangeEvent<HTMLInputElement>) => {
      setIsolationSettings(prev => ({
        ...prev,
        [category]: { is_isolated: e.target.checked }
      }))
      // If isolated, clear selections
      if (e.target.checked) {
        setSelections(prev => ({ ...prev, [category]: [] }))
      }
    }

    return (
      <div style={{ padding: 20 }}>
        <h2 style={{ marginBottom: 10 }}>{displayTitle}</h2>
        <p style={{ opacity: 0.8, marginBottom: 20, lineHeight: '1.4' }}>
          {displayDesc}
        </p>
        
        {guide?.examples && guide.examples.length > 0 && (
          <div style={{ marginBottom: 20, fontSize: '0.9rem', opacity: 0.7, background: '#f5f5f5', padding: 10, borderRadius: 8 }}>
            💡 Пример: {guide.examples.join(', ')}
          </div>
        )}

        <div style={{ marginBottom: 20, padding: 12, borderRadius: 10, background: '#fff3e0', border: '1px solid #ffe0b2' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', fontWeight: 600, fontSize: '0.9rem' }}>
            <input 
              type="checkbox" 
              checked={isIsolated} 
              onChange={handleIsolationToggle}
              style={{ width: 18, height: 18 }}
            />
            У меня нет никого в этой категории / Я в изоляции
          </label>
        </div>

        {isIsolated ? (
          <div style={{ marginBottom: 30, padding: 16, borderRadius: 12, background: '#e8f5e9', border: '1px solid #c8e6c9' }}>
            <div style={{ fontWeight: 700, color: '#2e7d32', marginBottom: 8 }}>🧘 Что делать:</div>
            <div style={{ lineHeight: '1.5', fontSize: '0.95rem' }}>{fallbackAdvice}</div>
          </div>
        ) : (
          <>
            <div style={{ marginBottom: 20 }}>
              <div style={{ fontWeight: 600, marginBottom: 10 }}>Выбери из списка:</div>
              {partners.length === 0 && <div style={{ opacity: 0.5, fontStyle: 'italic' }}>Пока никого нет</div>}
              <div style={{ display: 'grid', gap: 8 }}>
                {partners.map((p: PartnerOut) => (
                  <div 
                    key={p.id}
                    onClick={() => togglePartner(category, p.id)}
                    style={{
                      padding: 12,
                      borderRadius: 10,
                      border: selected.includes(p.id) ? '2px solid #3390ec' : '1px solid #ddd',
                      background: selected.includes(p.id) ? '#f0f8ff' : '#fff',
                      cursor: 'pointer',
                      fontWeight: 500,
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}
                  >
                    <div>
                      {selected.includes(p.id) ? '✅ ' : '⬜️ '} {p.name}
                    </div>
                    {p.contact_type && (
                      <div style={{ fontSize: '0.8rem', padding: '2px 6px', borderRadius: 4, background: '#eee', color: '#666' }}>
                        {p.contact_type === 'online' ? '🌐 Онлайн' : '🏠 Лично'}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div style={{ marginBottom: 30 }}>
              <div style={{ fontWeight: 600, marginBottom: 10 }}>Или добавь нового:</div>
              <div style={{ display: 'grid', gap: 10 }}>
                <input 
                  value={newPartnerName}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => setNewPartnerName(e.target.value)}
                  placeholder="Имя..."
                  style={{ padding: 10, borderRadius: 8, border: '1px solid #ddd', fontSize: '1rem' }}
                />
                
                <div style={{ display: 'flex', gap: 10 }}>
                  <button
                    onClick={() => setNewPartnerContactType('physical')}
                    style={{
                      flex: 1,
                      padding: 8,
                      borderRadius: 8,
                      border: `1px solid ${newPartnerContactType === 'physical' ? '#3390ec' : '#ddd'}`,
                      background: newPartnerContactType === 'physical' ? '#e3f2fd' : '#fff',
                      color: newPartnerContactType === 'physical' ? '#1565c0' : '#666',
                      cursor: 'pointer',
                      fontSize: '0.9rem'
                    }}
                  >
                    🏠 Лично
                  </button>
                  <button
                    onClick={() => setNewPartnerContactType('online')}
                    style={{
                      flex: 1,
                      padding: 8,
                      borderRadius: 8,
                      border: `1px solid ${newPartnerContactType === 'online' ? '#3390ec' : '#ddd'}`,
                      background: newPartnerContactType === 'online' ? '#e3f2fd' : '#fff',
                      color: newPartnerContactType === 'online' ? '#1565c0' : '#666',
                      cursor: 'pointer',
                      fontSize: '0.9rem'
                    }}
                  >
                    🌐 Онлайн
                  </button>
                </div>

                <button 
                  onClick={() => handleCreatePartner(category)}
                  disabled={isCreating || !newPartnerName}
                  style={{ padding: '12px', borderRadius: 8, border: 'none', background: '#3390ec', color: '#fff', cursor: 'pointer', fontWeight: 600 }}
                >
                  {isCreating ? 'Создаем...' : 'Добавить и выбрать'}
                </button>
              </div>
            </div>
          </>
        )}

        <div style={{ display: 'flex', gap: 10 }}>
          <button 
            onClick={handleBack}
            style={{ flex: 1, padding: 14, borderRadius: 12, border: 'none', background: '#eee', color: '#333', fontWeight: 600, cursor: 'pointer' }}
          >
            Назад
          </button>
          <button 
            onClick={handleNext}
            style={{ flex: 2, padding: 14, borderRadius: 12, border: 'none', background: '#3390ec', color: '#fff', fontWeight: 600, cursor: 'pointer' }}
          >
            {step === 'world' ? (submitting ? 'Создаем...' : 'Запустить проект 🚀') : 'Далее'}
          </button>
        </div>
      </div>
    )
  }

  if (step === 'source') return renderStep('source')
  if (step === 'ally') return renderStep('ally')
  if (step === 'protege') return renderStep('protege')
  if (step === 'world') return renderStep('world')

  return null
}
