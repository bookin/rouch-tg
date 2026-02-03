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

  return (
    <div className="page">
      <h1>🧩 Решение проблемы</h1>

      <form onSubmit={onSubmit} style={{ display: 'grid', gap: 8, marginTop: 12 }}>
        <textarea
          value={problem}
          onChange={(e) => setProblem(e.target.value)}
          placeholder="Опиши проблему (например: нестабильные доходы, конфликт в команде...)"
          rows={4}
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
          disabled={loading}
          style={{
            padding: 12,
            borderRadius: 10,
            border: 'none',
            background: 'var(--tg-theme-button-color, #3390ec)',
            color: 'var(--tg-theme-button-text-color, #fff)',
            fontWeight: 700,
            opacity: loading ? 0.7 : 1
          }}
        >
          {loading ? 'Думаю…' : 'Найти решение'}
        </button>
      </form>

      {error && (
        <div style={{ marginTop: 12, color: 'crimson' }}>
          {error}
        </div>
      )}

      {result && (
        <div style={{ display: 'grid', gap: 10, marginTop: 16 }}>
          <div style={{
            background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)',
            borderRadius: 10,
            padding: 12
          }}>
            <div style={{ fontWeight: 700 }}>Корень проблемы</div>
            <div style={{ marginTop: 6, whiteSpace: 'pre-wrap' }}>
              {result.root_cause || '—'}
            </div>
          </div>

          <div style={{
            background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)',
            borderRadius: 10,
            padding: 12
          }}>
            <div style={{ fontWeight: 700 }}>Противоположное действие</div>
            <div style={{ marginTop: 6, whiteSpace: 'pre-wrap' }}>
              {result.opposite_action || '—'}
            </div>
          </div>

          {Array.isArray(result.practice_steps) && result.practice_steps.length > 0 && (
            <div style={{
              background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)',
              borderRadius: 10,
              padding: 12
            }}>
              <div style={{ fontWeight: 700 }}>План (шаги)</div>
              <ol style={{ marginTop: 8, paddingLeft: 18 }}>
                {result.practice_steps.map((s: string, idx: number) => (
                  <li key={idx} style={{ marginBottom: 6 }}>{s}</li>
                ))}
              </ol>
            </div>
          )}

          {result.expected_outcome && (
            <div style={{
              background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)',
              borderRadius: 10,
              padding: 12
            }}>
              <div style={{ fontWeight: 700 }}>Ожидаемый результат</div>
              <div style={{ marginTop: 6, whiteSpace: 'pre-wrap' }}>
                {result.expected_outcome}
              </div>
            </div>
          )}

          {result.timeline_days && (
            <div style={{ opacity: 0.7 }}>
              Оценка срока: {result.timeline_days} дней
            </div>
          )}
        </div>
      )}
    </div>
  )
}

