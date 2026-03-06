import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { loginUser } from '../api/client'
import { Loader2, LogIn, ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export default function Login() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email || !password) {
      setError('Пожалуйста, заполни все поля')
      return
    }
    setLoading(true)
    setError(null)
    try {
      await loginUser({ username: email, password })
			const nextFromQuery = searchParams.get('next')
			const nextFromStorage = sessionStorage.getItem('auth_next') || localStorage.getItem('auth_next')
			const next = nextFromQuery || nextFromStorage
			sessionStorage.removeItem('auth_next')
			localStorage.removeItem('auth_next')
			navigate(next || '/')
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      if (detail === 'LOGIN_BAD_CREDENTIALS') {
        setError('Неверный email или пароль. Попробуй ещё раз — всё получится.')
      } else {
        setError('Что-то пошло не так. Попробуй через минутку.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-sm space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="text-5xl">🪷</div>
          <h1 className="text-2xl font-semibold text-foreground">
            Добро пожаловать
          </h1>
          <p className="text-sm text-muted-foreground">
            Войди, чтобы продолжить практику
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleLogin} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="email@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="password">Пароль</Label>
            <Input
              id="password"
              type="password"
              placeholder="******"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>

          {error && (
            <p className="text-sm text-red-400 bg-red-900/20 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <Button
            type="submit"
            className="w-full"
            disabled={loading}
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
            ) : (
              <LogIn className="w-4 h-4 mr-2" />
            )}
            Войти
          </Button>
        </form>

        {/* Link to register */}
        <div className="text-center">
          <button
            type="button"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            onClick={() => {
					const nextFromQuery = searchParams.get('next')
					const nextFromStorage = sessionStorage.getItem('auth_next') || localStorage.getItem('auth_next')
					const next = nextFromQuery || nextFromStorage
					navigate(`/register${next ? `?next=${encodeURIComponent(next)}` : ''}`)
				}}
          >
            Нет аккаунта? Зарегистрируйся
          </button>
        </div>

        {/* Back link */}
        <div className="text-center">
          <button
            type="button"
            className="text-xs text-muted-foreground/60 hover:text-muted-foreground transition-colors inline-flex items-center gap-1"
            onClick={() => navigate('/')}
          >
            <ArrowLeft className="w-3 h-3" />
            На главную
          </button>
        </div>
      </div>
    </div>
  )
}
