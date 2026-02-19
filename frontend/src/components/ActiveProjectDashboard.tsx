import { useState } from 'react'
import { ProjectStatusResponse, completeDailyProjectPlan } from '../api/client'

interface Props {
  data: ProjectStatusResponse
  onRefresh: () => void
}

export default function ActiveProjectDashboard({ data, onRefresh }: Props) {
  const { project, daily_plan } = data
  const [completedTasks, setCompletedTasks] = useState<string[]>([])
  const [notes, setNotes] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  if (!project) return null

  // Initialize completed tasks if daily plan is already completed
  
  const handleTaskToggle = (task: string) => {
    if (daily_plan?.is_completed) return // Read only if already completed today
    
    setCompletedTasks((prev: string[]) => {
      if (prev.includes(task)) {
        return prev.filter((t: string) => t !== task)
      } else {
        return [...prev, task]
      }
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
    <div style={{ display: 'grid', gap: 16 }}>
      
      {/* Header Card */}
      <div style={{ 
        background: 'linear-gradient(135deg, var(--tg-theme-button-color, #3390ec) 0%, #2196f3 100%)', 
        borderRadius: 16, 
        padding: 20, 
        color: '#fff', 
        boxShadow: '0 4px 12px rgba(33, 150, 243, 0.3)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
          <div>
            <div style={{ fontSize: '0.8rem', opacity: 0.9, fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Активный проект
            </div>
            <h2 style={{ margin: '4px 0 0 0', fontSize: '1.25rem', lineHeight: 1.3 }}>
              {project.problem}
            </h2>
          </div>
          <div style={{ 
            background: 'rgba(255,255,255,0.2)', 
            padding: '4px 10px', 
            borderRadius: 12, 
            fontSize: '0.85rem', 
            fontWeight: 700,
            backdropFilter: 'blur(4px)'
          }}>
            День {project.day_number}/{project.duration_days}
          </div>
        </div>

        {/* Progress Bar */}
        <div style={{ background: 'rgba(0,0,0,0.1)', height: 6, borderRadius: 3, overflow: 'hidden', marginTop: 16 }}>
          <div style={{ 
            width: `${progressPercent}%`, 
            height: '100%', 
            background: '#fff', 
            borderRadius: 3,
            transition: 'width 0.5s ease-out'
          }} />
        </div>
      </div>

      {/* Daily Plan Card */}
      {daily_plan ? (
        <div style={{ 
          background: 'var(--tg-theme-bg-color, #fff)', 
          borderRadius: 16, 
          padding: 16,
          border: '1px solid var(--tg-theme-secondary-bg-color, #eee)',
          boxShadow: '0 2px 8px rgba(0,0,0,0.05)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
            <div style={{ fontSize: '1.5rem' }}>📅</div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '1rem' }}>План на сегодня</div>
              <div style={{ fontSize: '0.85rem', opacity: 0.6 }}>Качество дня: <span style={{ color: 'var(--tg-theme-button-color, #3390ec)', fontWeight: 600 }}>{daily_plan.focus_quality}</span></div>
            </div>
          </div>

          <div style={{ display: 'grid', gap: 10 }}>
            {daily_plan.tasks.map((task, idx) => {
              const isChecked = daily_plan.is_completed || completedTasks.includes(task)
              return (
                <div 
                  key={idx}
                  onClick={() => handleTaskToggle(task)}
                  style={{ 
                    display: 'flex', 
                    gap: 12, 
                    padding: 12, 
                    borderRadius: 12, 
                    background: isChecked ? '#f0fff4' : 'var(--tg-theme-secondary-bg-color, #f5f5f5)',
                    border: isChecked ? '1px solid #c6f6d5' : '1px solid transparent',
                    cursor: daily_plan.is_completed ? 'default' : 'pointer',
                    transition: 'all 0.2s'
                  }}
                >
                  <div style={{ 
                    minWidth: 22, 
                    height: 22, 
                    borderRadius: 6, 
                    border: isChecked ? 'none' : '2px solid #ccc',
                    background: isChecked ? '#48bb78' : 'none',
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'center',
                    color: '#fff',
                    fontSize: '0.9rem'
                  }}>
                    {isChecked && '✓'}
                  </div>
                  <div style={{ 
                    fontSize: '0.95rem', 
                    textDecoration: isChecked ? 'line-through' : 'none',
                    opacity: isChecked ? 0.6 : 1
                  }}>
                    {task}
                  </div>
                </div>
              )
            })}
          </div>

          {!daily_plan.is_completed && (
            <div style={{ marginTop: 20, paddingTop: 16, borderTop: '1px solid #eee' }}>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Заметки к кофе-медитации (как прошел день?)..."
                rows={3}
                style={{
                  width: '100%',
                  padding: 12,
                  borderRadius: 10,
                  border: '1px solid var(--tg-theme-hint-color, #ccc)',
                  fontSize: '0.9rem',
                  resize: 'none',
                  outline: 'none',
                  marginBottom: 12,
                  fontFamily: 'inherit'
                }}
              />
              
              <button
                onClick={handleCompleteDay}
                disabled={isSubmitting || completedTasks.length === 0}
                style={{
                  width: '100%',
                  padding: '14px',
                  borderRadius: 12,
                  border: 'none',
                  background: completedTasks.length > 0 ? 'var(--tg-theme-button-color, #3390ec)' : '#ccc',
                  color: '#fff',
                  fontWeight: 700,
                  fontSize: '1rem',
                  cursor: completedTasks.length > 0 ? 'pointer' : 'not-allowed',
                  opacity: isSubmitting ? 0.7 : 1
                }}
              >
                {isSubmitting ? 'Сохраняем...' : '☕️ Завершить день (Кофе-медитация)'}
              </button>
            </div>
          )}

          {daily_plan.is_completed && (
            <div style={{ marginTop: 16, padding: 12, background: '#f0fff4', borderRadius: 10, textAlign: 'center', color: '#2f855a', fontWeight: 600, fontSize: '0.9rem' }}>
              ✨ День завершен! Ты молодец.
            </div>
          )}
        </div>
      ) : (
        <div style={{ padding: 20, textAlign: 'center', color: '#888', background: '#f5f5f5', borderRadius: 16 }}>
          План на сегодня еще не сформирован.
          <br/>Загляни в утренние сообщения!
        </div>
      )}

      {/* Strategy Summary Card */}
      <div style={{ background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)', borderRadius: 16, padding: 16 }}>
        <h3 style={{ margin: '0 0 12px 0', fontSize: '1rem', opacity: 0.7 }}>🔑 Стратегия успеха</h3>
        
        <div style={{ display: 'grid', gap: 12 }}>
          <div style={{ display: 'flex', gap: 10 }}>
            <div style={{ minWidth: 24, fontSize: '1.2rem' }}>🛑</div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.8rem', color: '#e65100' }}>STOP</div>
              <div style={{ fontSize: '0.9rem' }}>{project.strategy.stop_action}</div>
            </div>
          </div>
          
          <div style={{ display: 'flex', gap: 10 }}>
            <div style={{ minWidth: 24, fontSize: '1.2rem' }}>✅</div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.8rem', color: '#2e7d32' }}>START</div>
              <div style={{ fontSize: '0.9rem' }}>{project.strategy.start_action}</div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 10 }}>
            <div style={{ minWidth: 24, fontSize: '1.2rem' }}>🌱</div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.8rem', color: '#1565c0' }}>GROW</div>
              <div style={{ fontSize: '0.9rem' }}>{project.strategy.grow_action}</div>
            </div>
          </div>
        </div>
      </div>
      
    </div>
  )
}
