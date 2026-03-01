import { useState } from 'react'
import { requestEmailLink, dismissLinkPrompt } from '../api/client'
import { Mail, Send, Loader2, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface Props {
  onDismiss: () => void
}

export default function LinkAccountPrompt({ onDismiss }: Props) {
  const [email, setEmail] = useState('')
  const [sending, setSending] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSend = async () => {
    if (!email.includes('@')) {
      setError('Введи корректный email')
      return
    }
    setSending(true)
    setError(null)
    try {
      await requestEmailLink(email)
      setSent(true)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Ошибка отправки')
    } finally {
      setSending(false)
    }
  }

  const handleDismiss = async () => {
    try {
      await dismissLinkPrompt()
    } catch {
      // ignore
    }
    onDismiss()
  }

  if (sent) {
    return (
      <div className="rounded-xl bg-emerald-900/20 border border-emerald-600/30 p-4 space-y-2 mx-4 mt-4">
        <p className="text-sm text-emerald-300">
          📬 Письмо отправлено на <strong>{email}</strong>
        </p>
        <p className="text-xs text-muted-foreground">
          Открой почту и нажми на ссылку для подтверждения
        </p>
        <button
          type="button"
          onClick={onDismiss}
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          Закрыть
        </button>
      </div>
    )
  }

  return (
    <div className="rounded-xl bg-card/50 border border-border/50 p-4 space-y-3 mx-4 mt-4">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <Mail className="w-5 h-5 text-primary" />
          <p className="text-sm font-medium">Привяжи email</p>
        </div>
        <button type="button" onClick={handleDismiss} className="text-muted-foreground hover:text-foreground">
          <X className="w-4 h-4" />
        </button>
      </div>

      <p className="text-xs text-muted-foreground">
        Чтобы входить через браузер и не потерять данные — укажи email
      </p>

      <div className="flex gap-2">
        <Input
          type="email"
          placeholder="email@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="flex-1 text-sm"
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
        />
        <Button onClick={handleSend} disabled={sending} size="sm">
          {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </Button>
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  )
}
