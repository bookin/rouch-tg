import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  getProfile,
  updateProfile,
  requestEmailLink,
  changePassword,
  generateTelegramLink,
  isTelegramContext,
  logoutUser,
  type UserProfile,
  type TelegramLinkResponse,
} from '../api/client'
import {
  Loader2, Save, Mail, Send, Lock, KeyRound,
  User, Clock, Sun, Moon, LogOut, RefreshCw, Timer,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export default function Settings() {
  const navigate = useNavigate()
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Editable fields
  const [firstName, setFirstName] = useState('')
  const [occupation, setOccupation] = useState('')
  const [timezone, setTimezone] = useState('')
  const [morningEnabled, setMorningEnabled] = useState(true)
  const [eveningEnabled, setEveningEnabled] = useState(true)

  // Email linking
  const [emailInput, setEmailInput] = useState('')
  const [emailSending, setEmailSending] = useState(false)
  const [emailSent, setEmailSent] = useState(false)

  // Password change
  const [showPasswordForm, setShowPasswordForm] = useState(false)
  const [curPw, setCurPw] = useState('')
  const [newPw, setNewPw] = useState('')
  const [pwSaving, setPwSaving] = useState(false)

  // Telegram linking
  const [tgLink, setTgLink] = useState<TelegramLinkResponse | null>(null)
  const [tgLoading, setTgLoading] = useState(false)
  const [tgTimeLeft, setTgTimeLeft] = useState<number | null>(null)
  const tgTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    getProfile()
      .then((p) => {
        setProfile(p)
        setFirstName(p.first_name || '')
        setOccupation(p.occupation || '')
        setTimezone(p.timezone || 'UTC')
        setMorningEnabled(p.morning_enabled)
        setEveningEnabled(p.evening_enabled)
      })
      .catch(() => setError('Не удалось загрузить профиль'))
      .finally(() => setLoading(false))
  }, [])

  // Timer for Telegram link expiry
  useEffect(() => {
    if (!tgLink?.expires_at) return
    const updateTimer = () => {
      const diff = Math.max(0, Math.floor((new Date(tgLink.expires_at!).getTime() - Date.now()) / 1000))
      setTgTimeLeft(diff)
      if (diff <= 0) {
        setTgLink(null)
        setTgTimeLeft(null)
      }
    }
    updateTimer()
    tgTimerRef.current = setInterval(updateTimer, 1000)
    return () => { if (tgTimerRef.current) clearInterval(tgTimerRef.current) }
  }, [tgLink?.expires_at])

  const saveProfile = async () => {
    setSaving(true)
    setMsg(null)
    setError(null)
    try {
      await updateProfile({
        first_name: firstName || undefined,
        occupation: occupation || undefined,
        timezone,
        morning_enabled: morningEnabled,
        evening_enabled: eveningEnabled,
      })
      setMsg('Сохранено ✅')
    } catch {
      setError('Не удалось сохранить')
    } finally {
      setSaving(false)
    }
  }

  const handleEmailLink = async () => {
    if (!emailInput.includes('@')) return
    setEmailSending(true)
    setError(null)
    try {
      await requestEmailLink(emailInput)
      setEmailSent(true)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Ошибка отправки')
    } finally {
      setEmailSending(false)
    }
  }

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    if (newPw.length < 6) { setError('Минимум 6 символов'); return }
    setPwSaving(true)
    setError(null)
    try {
      await changePassword(curPw, newPw)
      setMsg('Пароль изменён ✅')
      setShowPasswordForm(false)
      setCurPw('')
      setNewPw('')
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Ошибка смены пароля')
    } finally {
      setPwSaving(false)
    }
  }

  const handleTelegramLink = async () => {
    setTgLoading(true)
    try {
      const data = await generateTelegramLink()
      setTgLink(data)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Ошибка генерации ссылки')
    } finally {
      setTgLoading(false)
    }
  }

  const handleLogout = () => {
    logoutUser()
    navigate('/login')
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  if (!profile) {
    return (
      <div className="text-center p-8 text-muted-foreground">
        Не удалось загрузить профиль
      </div>
    )
  }

  const isTg = isTelegramContext()

  return (
    <div className="max-w-lg mx-auto space-y-6 p-4 pb-24">
      <h1 className="text-xl font-semibold">⚙️ Настройки</h1>

      {/* Profile fields */}
      <section className="space-y-4 rounded-xl bg-card/50 p-4">
        <h2 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          <User className="w-4 h-4" /> Профиль
        </h2>

        <div className="space-y-1.5">
          <Label htmlFor="name">Имя</Label>
          <Input id="name" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="occ">Занятие</Label>
          <Input id="occ" value={occupation} onChange={(e) => setOccupation(e.target.value)}
            placeholder="Предприниматель, Менеджер..." />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="tz">Часовой пояс</Label>
          <Input id="tz" value={timezone} onChange={(e) => setTimezone(e.target.value)}
            placeholder="Europe/Moscow" />
        </div>
      </section>

      {/* Notifications */}
      <section className="space-y-3 rounded-xl bg-card/50 p-4">
        <h2 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          <Clock className="w-4 h-4" /> Уведомления
        </h2>

        <label className="flex items-center justify-between cursor-pointer">
          <span className="flex items-center gap-2 text-sm">
            <Sun className="w-4 h-4" /> Утренние сообщения
          </span>
          <button
            type="button"
            onClick={() => setMorningEnabled(!morningEnabled)}
            className={`w-10 h-6 rounded-full transition-colors ${morningEnabled ? 'bg-primary' : 'bg-muted'}`}
          >
            <div className={`w-4 h-4 rounded-full bg-white m-1 transition-transform ${morningEnabled ? 'translate-x-4' : ''}`} />
          </button>
        </label>

        <label className="flex items-center justify-between cursor-pointer">
          <span className="flex items-center gap-2 text-sm">
            <Moon className="w-4 h-4" /> Вечерние сообщения
          </span>
          <button
            type="button"
            onClick={() => setEveningEnabled(!eveningEnabled)}
            className={`w-10 h-6 rounded-full transition-colors ${eveningEnabled ? 'bg-primary' : 'bg-muted'}`}
          >
            <div className={`w-4 h-4 rounded-full bg-white m-1 transition-transform ${eveningEnabled ? 'translate-x-4' : ''}`} />
          </button>
        </label>
      </section>

      {/* Save */}
      <Button onClick={saveProfile} disabled={saving} className="w-full">
        {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Save className="w-4 h-4 mr-2" />}
        Сохранить
      </Button>

      {msg && <p className="text-sm text-emerald-400 text-center">{msg}</p>}
      {error && <p className="text-sm text-red-400 bg-red-900/20 rounded-lg px-3 py-2">{error}</p>}

      {/* Email linking */}
      <section className="space-y-3 rounded-xl bg-card/50 p-4">
        <h2 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          <Mail className="w-4 h-4" /> Email
        </h2>

        {profile.email ? (
          <div className="space-y-2">
            <p className="text-sm">{profile.email} {profile.is_verified && '✅'}</p>
          </div>
        ) : emailSent ? (
          <p className="text-sm text-emerald-400">
            📬 Письмо отправлено на {emailInput}. Проверь почту!
          </p>
        ) : (
          <div className="flex gap-2">
            <Input
              type="email"
              placeholder="email@example.com"
              value={emailInput}
              onChange={(e) => setEmailInput(e.target.value)}
              className="flex-1"
            />
            <Button onClick={handleEmailLink} disabled={emailSending} size="sm">
              {emailSending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </Button>
          </div>
        )}
      </section>

      {/* Password */}
      {profile.has_password && (
        <section className="space-y-3 rounded-xl bg-card/50 p-4">
          <h2 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
            <Lock className="w-4 h-4" /> Пароль
          </h2>

          {showPasswordForm ? (
            <form onSubmit={handleChangePassword} className="space-y-3">
              <Input type="password" placeholder="Текущий пароль" value={curPw}
                onChange={(e) => setCurPw(e.target.value)} />
              <Input type="password" placeholder="Новый пароль (мин. 6)" value={newPw}
                onChange={(e) => setNewPw(e.target.value)} />
              <div className="flex gap-2">
                <Button type="submit" size="sm" disabled={pwSaving}>
                  {pwSaving && <Loader2 className="w-4 h-4 animate-spin mr-1" />}
                  Сменить
                </Button>
                <Button type="button" variant="ghost" size="sm"
                  onClick={() => setShowPasswordForm(false)}>
                  Отмена
                </Button>
              </div>
            </form>
          ) : (
            <Button variant="outline" size="sm" onClick={() => setShowPasswordForm(true)}>
              <KeyRound className="w-4 h-4 mr-2" /> Сменить пароль
            </Button>
          )}
        </section>
      )}

      {/* Telegram linking (web only) */}
      {!isTg && !profile.telegram_id && (
        <section className="space-y-3 rounded-xl bg-card/50 p-4">
          <h2 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
            <Send className="w-4 h-4" /> Telegram
          </h2>

          {tgLink?.deep_link ? (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Открой ссылку ниже в Telegram, чтобы привязать бот к этому аккаунту:
              </p>
              <a
                href={tgLink.deep_link}
                target="_blank"
                rel="noopener noreferrer"
                className="block text-center bg-[#0088cc] hover:bg-[#0077b5] text-white rounded-lg px-4 py-2.5 text-sm font-medium transition-colors"
              >
                Открыть в Telegram
              </a>
              <div className="flex items-center justify-center">
                <img
                  src={`https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(tgLink.deep_link)}`}
                  alt="QR Code"
                  className="w-44 h-44 rounded-lg"
                />
              </div>
              <p className="text-xs text-center text-muted-foreground">
                Или отсканируй QR-код камерой телефона
              </p>

              {/* Timer + refresh */}
              {tgTimeLeft !== null && (
                <div className="flex items-center justify-between text-xs">
                  <span className={`flex items-center gap-1 ${tgTimeLeft < 300 ? 'text-amber-400' : 'text-muted-foreground'}`}>
                    <Timer className="w-3.5 h-3.5" />
                    {tgTimeLeft > 0
                      ? `Ссылка действует ${Math.floor(tgTimeLeft / 60)}:${String(tgTimeLeft % 60).padStart(2, '0')}`
                      : 'Ссылка истекла'}
                  </span>
                  <button
                    type="button"
                    onClick={handleTelegramLink}
                    disabled={tgLoading}
                    className="flex items-center gap-1 text-primary hover:text-primary/80 transition-colors"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${tgLoading ? 'animate-spin' : ''}`} />
                    Обновить
                  </button>
                </div>
              )}
            </div>
          ) : (
            <Button onClick={handleTelegramLink} disabled={tgLoading} variant="outline" size="sm">
              {tgLoading && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
              Привязать Telegram
            </Button>
          )}
        </section>
      )}

      {profile.telegram_id && (
        <section className="rounded-xl bg-card/50 p-4">
          <p className="text-sm text-muted-foreground flex items-center gap-2">
            <Send className="w-4 h-4" /> Telegram привязан ✅
          </p>
        </section>
      )}

      {/* Logout (web only) */}
      {!isTg && (
        <Button variant="ghost" className="w-full text-muted-foreground" onClick={handleLogout}>
          <LogOut className="w-4 h-4 mr-2" /> Выйти
        </Button>
      )}
    </div>
  )
}
