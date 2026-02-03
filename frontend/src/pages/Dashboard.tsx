import { useEffect, useState } from 'react'
import { getDailyQuote, getDailyActions } from '../api/client'
import { useTelegram } from '../hooks/useTelegram'

export default function Dashboard() {
  const { user } = useTelegram()
  const [quote, setQuote] = useState<any>(null)
  const [actions, setActions] = useState<any[]>([])
  
  useEffect(() => {
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
    
    fetchData()
  }, [])
  
  return (
    <div className="page">
      <h1>Привет, {user?.first_name || 'друг'}! 👋</h1>
      
      {/* Quote Card */}
      {quote && (
        <div style={{
          background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)',
          borderRadius: '12px',
          padding: '16px',
          margin: '16px 0'
        }}>
          <div style={{ fontSize: '20px', marginBottom: '8px' }}>💭</div>
          <p style={{ fontStyle: 'italic', marginBottom: '8px' }}>
            "{quote.text}"
          </p>
          <p style={{ fontSize: '12px', opacity: 0.7 }}>
            {quote.context}
          </p>
        </div>
      )}
      
      {/* Daily Actions */}
      <h2>🌱 4 действия на сегодня</h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {actions.map((action, index) => (
          <div key={action.id} style={{
            background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)',
            borderRadius: '8px',
            padding: '12px'
          }}>
            <div style={{ fontWeight: 'bold' }}>
              {index + 1}. {action.partner_name}
            </div>
            <div>{action.description}</div>
            <div style={{ fontSize: '12px', opacity: 0.7, marginTop: '4px' }}>
              🎯 {action.why}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
