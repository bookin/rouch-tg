import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { registerUser, loginUser } from '../api/client'
import { Loader2, UserPlus, ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export default function Register() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [firstName, setFirstName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!email || !password || !firstName) {
      setError('Пожалуйста, заполни все поля')
      return
    }
    if (password !== confirmPassword) {
      setError('Пароли не совпадают — проверь и попробуй снова')
      return
    }
    if (password.length < 6) {
      setError('Пароль должен быть не менее 6 символов')
      return
    }

    setLoading(true)
    setError(null)
    try {
      await registerUser({ email, password, first_name: firstName })
      // Auto-login after registration
      await loginUser({ username: email, password })
      navigate('/onboarding')
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      if (detail === 'REGISTER_USER_ALREADY_EXISTS') {
        setError('Этот email уже зарегистрирован. Попробуй войти.')
      } else {
        setError('Не удалось создать аккаунт. Попробуй через минутку.')
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
            Начни свой путь
          </h1>
          <p className="text-sm text-muted-foreground">
            Создай аккаунт и начни трансформацию
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleRegister} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="firstName">Как тебя зовут?</Label>
            <Input
              id="firstName"
              placeholder="Имя"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              autoComplete="given-name"
            />
          </div>

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
              autoComplete="new-password"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="confirmPassword">Повтори пароль</Label>
            <Input
              id="confirmPassword"
              type="password"
              placeholder="******"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              autoComplete="new-password"
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
              <UserPlus className="w-4 h-4 mr-2" />
            )}
            Создать аккаунт
          </Button>
        </form>

        {/* Link to login */}
        <div className="text-center">
          <button
            type="button"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            onClick={() => navigate('/login')}
          >
            Уже есть аккаунт? Войди
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
