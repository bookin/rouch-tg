import { FormEvent, useState } from 'react'
import { solveProblem } from '../api/client'

export default function Problem() {
  const [problem, setProblem] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!problem.trim()) return

    try {
      setError(null)
      setLoading(true)
      const data = await solveProblem(problem.trim())
      setResult(data)
    } catch (err: any) {
      setError(err?.message || 'Failed to solve problem')
    } finally {
      setLoading(false)
    }
  }

  const renderContent = (text: string) => {
    if (!text) return null;
    return <div style={{ whiteSpace: 'pre-wrap' }}>{text}</div>;
  };

  return (
    <div className="page" style={{ paddingBottom: 40 }}>
      <h1>🧩 Решение проблемы</h1>

      <p style={{ opacity: 0.8, fontSize: '0.9rem', marginBottom: 16 }}>
        Система проанализирует твой запрос через призму кармического менеджмента и предложит конкретный путь исправления ситуации.
      </p>

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

      {error && (
        <div style={{ padding: 12, borderRadius: 10, background: '#fff0f0', color: 'crimson', marginBottom: 16, border: '1px solid #ffcccc' }}>
          ⚠️ {error}
        </div>
      )}

      {result && (
        <div style={{ display: 'grid', gap: 16 }}>

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
          {result.practice_steps && result.practice_steps.length > 0 && (
            <div style={{ background: 'var(--tg-theme-bg-color, #fff)', borderRadius: 16, padding: 16, border: '1px solid var(--tg-theme-secondary-bg-color, #eee)' }}>
              <h3 style={{ margin: '0 0 12px 0', fontSize: '1.1rem' }}>📅 План на 30 дней</h3>
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
          )}

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
    </div>
  )
}

