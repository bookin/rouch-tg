import { useEffect, useState } from 'react'
import { getDailyQuote, getDailyActions, toggleDailyAction } from '../api/client'
import { useTelegram } from '../hooks/useTelegram'
import { Link } from 'react-router-dom'

export default function Dashboard() {
  const { user } = useTelegram()
  const [quote, setQuote] = useState<any>(null)
  const [actions, setActions] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  const fetchData = async () => {
    try {
      const [quoteData, actionsData] = await Promise.all([
        getDailyQuote(),
        getDailyActions()
      ])
      setQuote(quoteData)
      setActions(actionsData.actions)
    } catch (error) {
      console.error('Error fetching dashboard data:', error)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const handleToggleAction = async (id: string, currentStatus: boolean) => {
    try {
      setLoading(true)
      await toggleDailyAction(id, !currentStatus)
      // Update local state for immediate feedback
      setActions(prev => prev.map(a =>
        a.id === id ? { ...a, completed: !currentStatus } : a
      ))
    } catch (error) {
      console.error('Failed to toggle action:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page" style={{ paddingBottom: 80 }}>
      <h1>Привет, {user?.first_name || 'друг'}! 👋</h1>

      {/* Quote Card */}
      {quote && (
        <div style={{
          background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)',
          borderRadius: '16px',
          padding: '20px',
          margin: '16px 0',
          boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
          border: '1px solid rgba(0,0,0,0.05)'
        }}>
          <div style={{ fontSize: '24px', marginBottom: '12px' }}>💭</div>
          <p style={{ fontSize: '1.1rem', fontStyle: 'italic', marginBottom: '12px', lineHeight: 1.4, color: 'var(--tg-theme-text-color)' }}>
            "{quote.text}"
          </p>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <p style={{ fontSize: '13px', fontWeight: 600, color: 'var(--tg-theme-hint-color)' }}>
              {quote.author || 'Аноним'}
            </p>
            <p style={{ fontSize: '11px', opacity: 0.6, textTransform: 'uppercase', letterSpacing: 0.5 }}>
              {quote.context}
            </p>
          </div>
        </div>
      )}

      {/* Daily Actions Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 32, marginBottom: 16 }}>
        <h2 style={{ margin: 0, fontSize: '1.4rem' }}>🌱 4 действия</h2>
        <Link to="/meditation" style={{
          textDecoration: 'none',
          background: 'linear-gradient(45deg, #ff9800, #f44336)',
          color: '#fff',
          padding: '8px 16px',
          borderRadius: 25,
          fontSize: '0.85rem',
          fontWeight: 700,
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          boxShadow: '0 4px 10px rgba(255, 152, 0, 0.3)'
        }}>
          ☕️ Кофе-медитация
        </Link>
      </div>

      {/* Actions List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {actions.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px 0', opacity: 0.5 }}>
            Генерируем советы для тебя...
          </div>
        ) : (
          actions.map((action, index) => (
            <div
              key={action.id}
              onClick={() => handleToggleAction(action.id, action.completed)}
              style={{
                background: action.completed
                  ? 'rgba(76, 175, 80, 0.1)'
                  : 'var(--tg-theme-secondary-bg-color, #f5f5f5)',
                borderRadius: '16px',
                padding: '16px',
                display: 'flex',
                gap: '16px',
                alignItems: 'flex-start',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                border: action.completed
                  ? '1px solid rgba(76, 175, 80, 0.3)'
                  : '1px solid transparent',
                opacity: loading ? 0.7 : 1,
                position: 'relative',
                overflow: 'hidden'
              }}
            >
              <div style={{
                width: 24,
                height: 24,
                borderRadius: '6px',
                border: `2px solid ${action.completed ? '#4CAF50' : '#ddd'}`,
                background: action.completed ? '#4CAF50' : 'transparent',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                marginTop: 2
              }}>
                {action.completed && <span style={{ color: 'white', fontSize: 14 }}>✓</span>}
              </div>

              <div style={{ flex: 1 }}>
                <div style={{
                  fontWeight: 700,
                  fontSize: '0.9rem',
                  color: action.completed ? '#2e7d32' : 'inherit',
                  marginBottom: 4
                }}>
                  {action.partner_name}
                </div>
                <div style={{
                  fontSize: '1rem',
                  lineHeight: 1.4,
                  textDecoration: action.completed ? 'line-through' : 'none',
                  opacity: action.completed ? 0.6 : 1
                }}>
                  {action.description}
                </div>
                <div style={{
                  fontSize: '12px',
                  opacity: 0.6,
                  marginTop: 8,
                  fontStyle: 'italic'
                }}>
                  🎯 {action.why}
                </div>
              </div>

              {/* Seed Shortcut */}
              {action.completed && (
                <Link
                  to={`/seeds?text=${encodeURIComponent(action.description)}`}
                  onClick={(e) => e.stopPropagation()}
                  style={{
                    position: 'absolute',
                    right: 8,
                    top: 8,
                    background: '#fff',
                    borderRadius: '50%',
                    width: 32,
                    height: 32,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: '0 2px 5px rgba(0,0,0,0.1)',
                    textDecoration: 'none',
                    fontSize: '18px'
                  }}
                  title="Записать в журнал"
                >
                  🌱
                </Link>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}
