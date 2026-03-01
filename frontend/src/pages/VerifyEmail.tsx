import { useEffect, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { verifyEmailToken, setPasswordByToken } from '../api/client'
import { Loader2, CheckCircle2, XCircle, Lock, ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

type Step = 'verifying' | 'success' | 'set-password' | 'needs-merge' | 'error'

export default function VerifyEmail() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token')

  const [step, setStep] = useState<Step>('verifying')
  const [error, setError] = useState<string | null>(null)
  const [email, setEmail] = useState('')
  const [mergeSourceId, setMergeSourceId] = useState<number | null>(null)
  const [pendingMerge, setPendingMerge] = useState(false)

  const [password1, setPassword1] = useState('')
  const [password2, setPassword2] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!token) {
      setStep('error')
      setError('Ссылка повреждена — токен отсутствует')
      return
    }

    verifyEmailToken(token)
      .then((data) => {
        setEmail(data.email || '')

        const needsMerge = !!data.needs_merge
        const needsPassword = !!data.needs_password

        if (needsMerge) {
          setMergeSourceId(data.merge_source_id)
          setPendingMerge(true)
        }

        if (needsPassword) {
          setStep('set-password')
        } else if (needsMerge) {
          setStep('needs-merge')
        } else {
          setStep('success')
        }
      })
      .catch(() => {
        setStep('error')
        setError('Ссылка недействительна или устарела')
      })
  }, [token])

  const handleSetPassword = async (e: React.FormEvent) => {
    e.preventDefault()
    if (password1.length < 6) {
      setError('Пароль — минимум 6 символов')
      return
    }
    if (password1 !== password2) {
      setError('Пароли не совпадают')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await setPasswordByToken(token!, password1)
      if (pendingMerge) {
        setStep('needs-merge')
      } else {
        setStep('success')
      }
    } catch {
      setError('Не удалось сохранить пароль. Попробуй ещё раз.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-sm space-y-6">
        {/* Verifying */}
        {step === 'verifying' && (
          <div className="text-center space-y-4">
            <Loader2 className="w-10 h-10 animate-spin mx-auto text-primary" />
            <p className="text-muted-foreground">Подтверждаем email...</p>
          </div>
        )}

        {/* Success */}
        {step === 'success' && (
          <div className="text-center space-y-4">
            <CheckCircle2 className="w-12 h-12 mx-auto text-emerald-400" />
            <h1 className="text-xl font-semibold">Email подтверждён ✨</h1>
            <p className="text-sm text-muted-foreground">
              {email && `${email} успешно привязан.`} Теперь можешь входить через браузер.
            </p>
            <Button onClick={() => navigate('/')} className="w-full">
              Перейти в приложение
            </Button>
          </div>
        )}

        {/* Set Password */}
        {step === 'set-password' && (
          <div className="space-y-6">
            <div className="text-center space-y-2">
              <Lock className="w-10 h-10 mx-auto text-primary" />
              <h1 className="text-xl font-semibold">Придумай пароль</h1>
              <p className="text-sm text-muted-foreground">
                Email {email} подтверждён! Теперь задай пароль для входа через браузер.
              </p>
            </div>

            {pendingMerge && (
              <div className="rounded-lg bg-amber-900/20 border border-amber-600/30 px-3 py-2">
                <p className="text-xs text-amber-300 flex items-center gap-1.5">
                  <ArrowRight className="w-3.5 h-3.5 shrink-0" />
                  После установки пароля предложим объединить аккаунты
                </p>
              </div>
            )}

            <form onSubmit={handleSetPassword} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="pw1">Пароль</Label>
                <Input
                  id="pw1"
                  type="password"
                  placeholder="Минимум 6 символов"
                  value={password1}
                  onChange={(e) => setPassword1(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="pw2">Повтори пароль</Label>
                <Input
                  id="pw2"
                  type="password"
                  placeholder="Ещё раз"
                  value={password2}
                  onChange={(e) => setPassword2(e.target.value)}
                />
              </div>

              {error && (
                <p className="text-sm text-red-400 bg-red-900/20 rounded-lg px-3 py-2">{error}</p>
              )}

              <Button type="submit" className="w-full" disabled={saving}>
                {saving && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
                Сохранить пароль
              </Button>
            </form>
          </div>
        )}

        {/* Needs Merge */}
        {step === 'needs-merge' && (
          <div className="text-center space-y-4">
            <div className="text-4xl">🔗</div>
            <h1 className="text-xl font-semibold">Найден другой аккаунт</h1>
            <p className="text-sm text-muted-foreground">
              Email <strong>{email}</strong> уже привязан к другому аккаунту.
              Можешь объединить их — все данные сольются в одно место.
            </p>
            <Button
              onClick={() => navigate(`/merge?source=${mergeSourceId}`)}
              className="w-full"
            >
              Посмотреть и объединить
            </Button>
            <button
              type="button"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
              onClick={() => navigate('/')}
            >
              Пропустить — решу позже
            </button>
          </div>
        )}

        {/* Error */}
        {step === 'error' && (
          <div className="text-center space-y-4">
            <XCircle className="w-12 h-12 mx-auto text-red-400" />
            <h1 className="text-xl font-semibold">Ошибка</h1>
            <p className="text-sm text-muted-foreground">{error}</p>
            <Button variant="outline" onClick={() => navigate('/')}>
              На главную
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
