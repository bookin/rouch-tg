import { FormEvent, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  solveProblem,
  updateUserFocus,
  getProblemsHistory,
  activateProblem,
  getPartners,
  addProblemToCalendar,
  getActiveProject,
  ProjectStatusResponse
} from '../api/client'
import ActiveProjectDashboard from '../components/ActiveProjectDashboard'
import PartnerWizard from '../components/PartnerWizard'

export default function Problem() {
  const navigate = useNavigate()
  const [problem, setProblem] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const [history, setHistory] = useState<any[]>([])
  const [partners, setPartners] = useState<any[]>([])
  const [selectedPartners, setSelectedPartners] = useState<string[]>([])
  const [showHistory, setShowHistory] = useState(false)
  // Режим уточняющих вопросов (Q&A), если агенту не хватает ясности
  const [needsClarification, setNeedsClarification] = useState(false)
  const [clarifyingQuestions, setClarifyingQuestions] = useState<string[]>([])
  const [clarificationText, setClarificationText] = useState('')
  const [initialProblem, setInitialProblem] = useState('')
  const [sessionId, setSessionId] = useState<string | null>(null)
  
  const [activeProjectData, setActiveProjectData] = useState<ProjectStatusResponse | null>(null)
  const [showProblemForm, setShowProblemForm] = useState(true)
  const [showWizard, setShowWizard] = useState(false)

  const loadData = async () => {
    try {
      const [histData, partData, projData] = await Promise.all([
        getProblemsHistory(),
        getPartners(),
        getActiveProject()
      ])
      setHistory(histData.history || [])
      setPartners(partData.partners || [])
      setActiveProjectData(projData)
      
      // If we have an active project, hide the form by default
      if (projData && projData.has_active_project) {
        setShowProblemForm(false)
      } else {
        setShowProblemForm(true)
      }
    } catch (e) {
      console.error('Failed to load data', e)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!problem.trim()) return

    try {
      setError(null)
      setSuccess(null)
      setLoading(true)
      const currentProblem = problem.trim()
      const data = await solveProblem({ problem: currentProblem })

      // Если агент просит уточнения и дал 1–3 вопроса — переходим в режим уточнения
      if (data?.needs_clarification && Array.isArray(data.clarifying_questions) && data.clarifying_questions.length > 0) {
        setNeedsClarification(true)
        setClarifyingQuestions(data.clarifying_questions.slice(0, 3))
        setClarificationText('')
        setInitialProblem(currentProblem)
        setSessionId(data.session_id || null)
        setResult(null)
      } else {
        setResult(data)
        setSessionId(data.session_id || null)
        await loadData() // Refresh history (and grab new history_id if needed)
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to solve problem')
    } finally {
      setLoading(false)
    }
  }

  const onClarificationSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!clarificationText.trim()) return

    try {
      setError(null)
      setSuccess(null)
      setLoading(true)

      if (!sessionId) {
        setError('Сессия диагностики утеряна. Попробуй начать заново.')
        setNeedsClarification(false)
        setClarifyingQuestions([])
        return
      }

      const baseProblem = initialProblem || problem.trim()

      const data = await solveProblem({
        problem: baseProblem,
        session_id: sessionId,
        diagnostic_answer: clarificationText.trim()
      })

      // Check if the agent needs MORE clarification (multi-step diagnostic)
      if (data?.needs_clarification && Array.isArray(data.clarifying_questions) && data.clarifying_questions.length > 0) {
        setNeedsClarification(true)
        setClarifyingQuestions(data.clarifying_questions.slice(0, 3))
        setClarificationText('')
        setSessionId(data.session_id || sessionId)
        // Keep result null so we don't show empty dashboard
        setResult(null)
      } else {
        // Diagnostic complete - show final solution
        setResult(data)
        setNeedsClarification(false)
        setClarifyingQuestions([])
        setClarificationText('')
        setSessionId(data.session_id || sessionId)
        await loadData()
      }
    } catch (err: any) {
      setError(err?.message || 'Не удалось обработать уточнения')
    } finally {
      setLoading(false)
    }
  }

  const handleActivateHistory = async (h: any) => {
    // This activates the problem in history (legacy) AND shows the result
    try {
      setLoading(true)
      await activateProblem(h.id)
      setResult(h.solution)
      // Ensure result has history_id for project activation
      setResult((prev: any) => ({ ...prev, history_id: h.id }))
      
      setProblem(h.problem_text)
      setSuccess('Проблема выбрана из истории.')
      setShowHistory(false)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } catch (err: any) {
      setError('Не удалось активировать проблему')
    } finally {
      setLoading(false)
    }
  }
  
  const handleStartProject = () => {
    if (!result || !result.history_id) {
      setError('Невозможно создать проект: отсутствует ID истории. Попробуйте обновить страницу.')
      return
    }
    setShowWizard(true)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleWizardComplete = (projData: ProjectStatusResponse) => {
    setActiveProjectData(projData)
    setSuccess('🚀 Кармический проект успешно запущен! Твой план на 30 дней готов.')
    setResult(null)
    setShowProblemForm(false)
    setShowWizard(false)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleWizardCancel = () => {
    setShowWizard(false)
  }

  const togglePartner = (id: string) => {
    setSelectedPartners(prev =>
      prev.includes(id) ? prev.filter(p => p !== id) : [...prev, id]
    )
  }

  const handleSetFocus = async () => {
    if (!result) return;
    try {
      setLoading(true);
      await updateUserFocus(result.problem || problem);
      setSuccess('Цель успешно установлена! Теперь твой мудрый менеджер будет помогать тебе в её достижении.');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (err: any) {
      setError('Не удалось обновить цель');
    } finally {
      setLoading(false);
    }
  };

  const handleStartPractice = () => {
    if (!result) return;
    const desc = encodeURIComponent(`STOP: ${result.stop_action}\nSTART: ${result.start_action}`);
    const parts = selectedPartners.length > 0 ? `&partner_ids=${selectedPartners.join(',')}` : '';
    navigate(`/journal?description=${desc}${parts}`);
  };

  const handleAddToCalendar = async () => {
    if (!result?.practice_steps) return;
    try {
      setLoading(true);
      await addProblemToCalendar(result.practice_steps);
      setSuccess('План на 30 дней успешно добавлен в твой календарь! 📅');
    } catch (err) {
      setError('Не удалось добавить план в календарь');
    } finally {
      setLoading(false);
    }
  };

  const renderContent = (text: string) => {
    if (!text) return null;
    return <div style={{ whiteSpace: 'pre-wrap' }}>{text}</div>;
  };

  return (
    <div className="page" style={{ paddingBottom: 40 }}>
      <h1>🧩 Решение проблемы</h1>

      {showWizard && result?.history_id ? (
        <PartnerWizard 
          historyId={result.history_id}
          onComplete={handleWizardComplete}
          onCancel={handleWizardCancel}
        />
      ) : (
        <>
          {/* ACTIVE PROJECT DASHBOARD */}
          {activeProjectData?.has_active_project && activeProjectData.project && (
        <div style={{ marginBottom: 30 }}>
           <ActiveProjectDashboard data={activeProjectData} onRefresh={loadData} />
           
           {!showProblemForm && (
             <button 
               onClick={() => setShowProblemForm(true)}
               style={{
                 marginTop: 20,
                 background: 'none',
                 border: '1px dashed #ccc',
                 width: '100%',
                 padding: 12,
                 borderRadius: 12,
                 color: '#888',
                 fontSize: '0.9rem',
                 cursor: 'pointer'
               }}
             >
               🔍 Разобрать другую проблему (не прерывая проект)
             </button>
           )}
        </div>
      )}

      {/* PROBLEM FORM */}
      {showProblemForm && (
        <>
          <p style={{ opacity: 0.8, fontSize: '0.9rem', marginBottom: 16 }}>
            Система проанализирует твой запрос через призму кармического менеджмента и предложит конкретный путь исправления ситуации.
          </p>

          {needsClarification && clarifyingQuestions.length > 0 && (
            <form
              onSubmit={onClarificationSubmit}
              style={{
                marginBottom: 20,
                padding: 16,
                borderRadius: 16,
                background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)',
                border: '1px solid rgba(0,0,0,0.05)',
              }}
            >
              <h3 style={{ margin: '0 0 10px 0', fontSize: '1rem' }}>🧐 Нужно чуть больше деталей</h3>
              <p style={{ margin: '0 0 10px 0', fontSize: '0.9rem', opacity: 0.8 }}>
                Ответь одним сообщением на вопросы ниже — так система сможет точнее увидеть корень проблемы.
              </p>

              <ol style={{ paddingLeft: 18, margin: '0 0 12px 0', fontSize: '0.9rem' }}>
                {clarifyingQuestions.map((q, idx) => (
                  <li key={idx} style={{ marginBottom: 4 }}>{q}</li>
                ))}
              </ol>

              <textarea
                value={clarificationText}
                onChange={(e) => setClarificationText(e.target.value)}
                placeholder="Напиши свои ответы одним сообщением..."
                rows={4}
                style={{
                  marginTop: 8,
                  width: '100%',
                  padding: 10,
                  borderRadius: 10,
                  border: '1px solid var(--tg-theme-hint-color, #bbb)',
                  fontSize: '0.95rem',
                  resize: 'none',
                  outline: 'none',
                  background: 'var(--tg-theme-bg-color, #fff)',
                  color: 'var(--tg-theme-text-color, #000)',
                }}
              />

              <button
                type="submit"
                disabled={loading}
                style={{
                  marginTop: 10,
                  padding: '10px 16px',
                  borderRadius: 10,
                  border: 'none',
                  background: 'var(--tg-theme-button-color, #3390ec)',
                  color: 'var(--tg-theme-button-text-color, #fff)',
                  fontWeight: 600,
                  fontSize: '0.95rem',
                  cursor: loading ? 'default' : 'pointer',
                  opacity: loading ? 0.7 : 1,
                }}
              >
                {loading ? 'Анализирую уточнения…' : 'Отправить уточнения'}
              </button>
            </form>
          )}

          {history.length > 0 && (
            <div style={{ marginBottom: 20 }}>
              <button
                onClick={() => setShowHistory(!showHistory)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--tg-theme-button-color, #3390ec)',
                  fontSize: '0.9rem',
                  fontWeight: 600,
                  padding: 0,
                  cursor: 'pointer',
                  marginBottom: 10,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4
                }}
              >
                {showHistory ? '🔼 Скрыть историю' : `📜 Показать историю (${history.length})`}
              </button>

              {showHistory && (
                <div style={{ display: 'grid', gap: 8, maxHeight: 200, overflowY: 'auto', padding: 4 }}>
                  {history.map(h => (
                    <div
                      key={h.id}
                      onClick={() => handleActivateHistory(h)}
                      style={{
                        padding: 12,
                        borderRadius: 10,
                        background: h.is_active ? '#e3f2fd' : 'var(--tg-theme-secondary-bg-color, #f5f5f5)',
                        border: h.is_active ? '1px solid #2196f3' : '1px solid transparent',
                        cursor: 'pointer',
                        fontSize: '0.9rem'
                      }}
                    >
                      <div style={{ fontWeight: h.is_active ? 700 : 500 }}>{h.problem_text}</div>
                      <div style={{ fontSize: '0.75rem', opacity: 0.6, marginTop: 4 }}>
                        {new Date(h.created_at).toLocaleDateString()} {h.is_active && '• Активна'}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12, marginBottom: 20 }}>
            <textarea
              value={problem}
              onChange={(e) => setProblem(e.target.value)}
              placeholder="Опиши проблему как можно точнее..."
              rows={4}
              style={{
                padding: 12,
                borderRadius: 12,
                border: '1px solid var(--tg-theme-hint-color, #ccc)',
                background: 'var(--tg-theme-bg-color, #fff)',
                color: 'var(--tg-theme-text-color, #000)',
                fontSize: '1rem',
                resize: 'none',
                outline: 'none',
                boxShadow: '0 2px 8px rgba(0,0,0,0.05)'
              }}
            />
            <button
              type="submit"
              disabled={loading}
              style={{
                padding: '14px 20px',
                borderRadius: 12,
                border: 'none',
                background: 'var(--tg-theme-button-color, #3390ec)',
                color: 'var(--tg-theme-button-text-color, #fff)',
                fontWeight: 700,
                fontSize: '1rem',
                opacity: loading ? 0.7 : 1,
                cursor: loading ? 'default' : 'pointer',
                transition: 'transform 0.1s active'
              }}
            >
              {loading ? 'Анализирую отпечатки…' : 'Найти решение'}
            </button>
          </form>
        </>
      )}

      {error && (
        <div style={{ padding: 12, borderRadius: 10, background: '#fff0f0', color: 'crimson', marginBottom: 16, border: '1px solid #ffcccc' }}>
          ⚠️ {error}
        </div>
      )}

      {success && (
        <div style={{ padding: 12, borderRadius: 10, background: '#f0fff0', color: 'darkgreen', marginBottom: 16, border: '1px solid #ccffcc' }}>
          ✨ {success}
        </div>
      )}

      {result && (
        <div style={{ display: 'grid', gap: 16 }}>

          {/* MAIN CTA: ACTIVATE PROJECT */}
          <div style={{ 
            background: 'linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%)', 
            borderRadius: 16, 
            padding: 20, 
            border: '1px solid #90caf9',
            boxShadow: '0 4px 12px rgba(33, 150, 243, 0.15)' 
          }}>
            <h3 style={{ margin: '0 0 8px 0', fontSize: '1.2rem', color: '#1565c0' }}>Решение найдено! 🚀</h3>
            <p style={{ margin: '0 0 16px 0', fontSize: '0.95rem', color: '#0d47a1' }}>
              Хочешь, чтобы я провел тебя через 30-дневный путь исправления этой ситуации? 
              Я буду давать тебе задания каждый день и поддерживать тебя.
            </p>
            <button 
              onClick={handleStartProject}
              disabled={loading}
              style={{
                width: '100%',
                padding: '14px',
                borderRadius: 12,
                border: 'none',
                background: '#1565c0',
                color: '#fff',
                fontWeight: 700,
                fontSize: '1.05rem',
                cursor: 'pointer',
                boxShadow: '0 4px 6px rgba(21, 101, 192, 0.3)'
              }}
            >
              {loading ? 'Создаю проект...' : 'Начать Кармический Проект'}
            </button>
          </div>

          {/* Section: Diagnostics */}
          <div style={{ background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)', borderRadius: 16, padding: 16 }}>
            <h3 style={{ margin: '0 0 10px 0', fontSize: '1.1rem' }}>🔍 Диагностика</h3>

            <div style={{ marginBottom: 14 }}>
              <div style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--tg-theme-hint-color, #888)', textTransform: 'uppercase' }}>Корень проблемы</div>
              <div style={{ marginTop: 4, fontWeight: 500 }}>{result.root_cause}</div>
            </div>

            {result.imprint_logic && (
              <div>
                <div style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--tg-theme-hint-color, #888)', textTransform: 'uppercase' }}>Механизм отпечатка</div>
                <div style={{ marginTop: 4, fontSize: '0.95rem', lineHeight: '1.4' }}>{result.imprint_logic}</div>
              </div>
            )}

            <div style={{ marginTop: 16 }}>
              <div style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--tg-theme-hint-color, #888)', textTransform: 'uppercase', marginBottom: 8 }}>С кем практиковать (Партнеры)</div>
              <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 8 }}>
                {partners.length === 0 && <div style={{ fontSize: '0.85rem', opacity: 0.5 }}>У тебя пока нет партнеров</div>}
                {partners.map((p: any) => (
                  <div
                    key={p.id}
                    onClick={() => togglePartner(p.id)}
                    style={{
                      padding: '6px 12px',
                      borderRadius: 20,
                      background: selectedPartners.includes(p.id) ? 'var(--tg-theme-button-color, #3390ec)' : '#eee',
                      color: selectedPartners.includes(p.id) ? '#fff' : '#666',
                      fontSize: '0.8rem',
                      whiteSpace: 'nowrap',
                      cursor: 'pointer',
                      transition: '0.2s'
                    }}
                  >
                    {p.name}
                  </div>
                ))}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 16 }}>
              <button
                onClick={handleSetFocus}
                disabled={loading}
                style={{
                  padding: '10px',
                  borderRadius: 10,
                  border: '1px solid var(--tg-theme-button-color, #3390ec)',
                  background: 'none',
                  color: 'var(--tg-theme-button-color, #3390ec)',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                🎯 Просто цель
              </button>
              <button
                onClick={handleStartPractice}
                style={{
                  padding: '10px',
                  borderRadius: 10,
                  border: 'none',
                  background: 'var(--tg-theme-button-color, #3390ec)',
                  color: 'var(--tg-theme-button-text-color, #fff)',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                🌱 В журнал
              </button>
            </div>
          </div>

          {/* Section: Action Plan STOP-START-GROW */}
          <div style={{ display: 'grid', gap: 10 }}>
            <h3 style={{ margin: '4px 0 4px 4px', fontSize: '1.1rem' }}>🚀 План действий</h3>

            <div style={{ background: '#fff9f0', borderLeft: '4px solid #ffa000', borderRadius: '0 12px 12px 0', padding: 12 }}>
              <div style={{ fontWeight: 700, color: '#e65100' }}>🛑 STOP: Что прекратить</div>
              <div style={{ marginTop: 4 }}>{result.stop_action}</div>
            </div>

            <div style={{ background: '#f0fff0', borderLeft: '4px solid #4caf50', borderRadius: '0 12px 12px 0', padding: 12 }}>
              <div style={{ fontWeight: 700, color: '#2e7d32' }}>✅ START: Что начать</div>
              <div style={{ marginTop: 4 }}>{result.start_action}</div>
            </div>

            <div style={{ background: '#f0f4ff', borderLeft: '4px solid #2196f3', borderRadius: '0 12px 12px 0', padding: 12 }}>
              <div style={{ fontWeight: 700, color: '#1565c0' }}>☕️ GROW: Как поливать</div>
              <div style={{ marginTop: 4 }}>{result.grow_action}</div>
            </div>
          </div>

          {/* Section: Detailed Steps */}
          <div style={{ background: 'var(--tg-theme-bg-color, #fff)', borderRadius: 16, padding: 16, border: '1px solid var(--tg-theme-secondary-bg-color, #eee)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <h3 style={{ margin: 0, fontSize: '1.1rem' }}>📅 План на 30 дней</h3>
              <button
                onClick={handleAddToCalendar}
                disabled={loading}
                style={{
                  background: '#e3f2fd',
                  color: '#2196f3',
                  border: 'none',
                  borderRadius: 8,
                  padding: '6px 12px',
                  fontSize: '0.8rem',
                  fontWeight: 700,
                  cursor: 'pointer'
                }}
              >
                {loading ? '...' : '✍️ В календарь'}
              </button>
            </div>
            <div style={{ display: 'grid', gap: 10 }}>
              {result.practice_steps.map((step: string, i: number) => (
                <div key={i} style={{ display: 'flex', gap: 10, fontSize: '0.95rem' }}>
                  <div style={{ minWidth: 24, height: 24, borderRadius: '50%', background: 'var(--tg-theme-secondary-bg-color, #eee)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.8rem', fontWeight: 700 }}>
                    {i + 1}
                  </div>
                  <div>{step}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Section: Outcome & Tips */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            {result.expected_outcome && (
              <div style={{ flex: '1 1 200px', background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)', borderRadius: 12, padding: 12 }}>
                <div style={{ fontWeight: 700, fontSize: '0.8rem' }}>Ожидаемый результат</div>
                <div style={{ marginTop: 4, fontSize: '0.9rem' }}>{result.expected_outcome}</div>
              </div>
            )}
            {result.success_tip && (
              <div style={{ flex: '1 1 200px', background: '#fffbe6', borderRadius: 12, padding: 12, border: '1px solid #ffe58f' }}>
                <div style={{ fontWeight: 700, fontSize: '0.8rem', color: '#856404' }}>💡 Совет мастера</div>
                <div style={{ marginTop: 4, fontSize: '0.9rem' }}>{result.success_tip}</div>
              </div>
            )}
          </div>

          {/* Section: Key rule && practice */}
          {(result.rules && result.rules.length > 0) || (result.practices && result.practices.length > 0) ? (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 10 }}>
              {result.rules && result.rules.length > 0 && (
                <div style={{ flex: '1 1 240px', background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)', borderRadius: 12, padding: 12 }}>
                  <div style={{ fontWeight: 700, fontSize: '0.85rem', marginBottom: 4 }}>📜 Правило, на котором основан план</div>
                  {(() => {
                    const rule = result.rules[0]
                    if (!rule) return null
                    return (
                      <>
                        {rule.title && (
                          <div style={{ fontWeight: 600, marginBottom: 4 }}>{rule.title}</div>
                        )}
                        {rule.number && (
                          <div style={{ fontSize: '0.8rem', opacity: 0.6, marginBottom: 4 }}>№ {rule.number}</div>
                        )}
                        <div style={{ fontSize: '0.9rem' }}>
                          {renderContent((rule.content || '').slice(0, 400))}
                        </div>
                      </>
                    )
                  })()}
                </div>
              )}

              {result.practices && result.practices.length > 0 && (
                <div style={{ flex: '1 1 240px', background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)', borderRadius: 12, padding: 12 }}>
                  <div style={{ fontWeight: 700, fontSize: '0.85rem', marginBottom: 4 }}>🧘 Рекомендуемая практика дня</div>
                  {(() => {
                    const practice = result.practices[0]
                    if (!practice) return null
                    const title = practice.name || practice.title
                    return (
                      <>
                        {title && (
                          <div style={{ fontWeight: 600, marginBottom: 4 }}>{title}</div>
                        )}
                        {practice.duration && (
                          <div style={{ fontSize: '0.8rem', opacity: 0.6, marginBottom: 4 }}>{practice.duration} мин</div>
                        )}
                        <div style={{ fontSize: '0.9rem' }}>
                          {renderContent((practice.content || '').slice(0, 400))}
                        </div>
                      </>
                    )
                  })()}
                </div>
              )}
            </div>
          ) : null}

          {/* Section: Concepts from RAG */}
          {result.concepts && result.concepts.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <h3 style={{ margin: '0 0 10px 4px', fontSize: '1.1rem', opacity: 0.6 }}>📖 Полезные концепции</h3>
              <div style={{ display: 'grid', gap: 10 }}>
                {result.concepts.map((concept: any, i: number) => (
                  <details key={i} style={{ background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)', borderRadius: 12, padding: 12 }}>
                    <summary style={{ fontWeight: 700, cursor: 'pointer', outline: 'none' }}>{concept.title}</summary>
                    <div style={{ marginTop: 10, fontSize: '0.9rem', borderTop: '1px solid #ddd', paddingTop: 10 }}>
                      {renderContent(concept.content)}
                    </div>
                  </details>
                ))}
              </div>
            </div>
          )}

          {/* Section: Correlations table context */}
          {result.correlations && result.correlations.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <h3 style={{ margin: '0 0 10px 4px', fontSize: '1.1rem', opacity: 0.6 }}>⛓ Прямые корреляции</h3>
              <div style={{ display: 'grid', gap: 8 }}>
                {result.correlations.map((corr: any, i: number) => (
                  <div key={i} style={{ fontSize: '0.85rem', padding: 10, borderRadius: 10, border: '1px dashed #ccc' }}>
                    <strong>{corr.problem}</strong> → <i>{corr.solution}</i>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div style={{ textAlign: 'center', opacity: 0.5, fontSize: '0.8rem', marginTop: 10 }}>
            {result.timeline_days ? `Оценка времени проявления: ~${result.timeline_days} дней` : ''}
          </div>

        </div>
      )}
        </>
      )}
    </div>
  )
}

