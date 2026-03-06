import {useEffect, useMemo, useRef, useState} from 'react'
import {
	dismissLinkPrompt,
	generateTelegramLink,
	getProfile,
	requestEmailLink,
	setPassword,
	type TelegramLinkResponse,
	type UserProfile,
	isTelegramContext,
} from '@/api/client'
import {Button} from '@/components/ui/button'
import {Input} from '@/components/ui/input'
import {Loader2, Mail, Lock, QrCode, RefreshCw, Copy, ExternalLink, X} from 'lucide-react'

type GateStep = 'email' | 'password' | 'telegram' | null

function shouldShowEmailPrompt(profile: UserProfile): boolean {
	return !profile.email && !profile.link_prompt_dismissed
}

function shouldShowPasswordPrompt(profile: UserProfile): boolean {
	return Boolean(profile.email) && !profile.has_password
}

function shouldShowTelegramPrompt(profile: UserProfile): boolean {
	return !isTelegramContext() && !profile.telegram_id
}

export default function AccountLinkGate() {
	const [loading, setLoading] = useState(true)
	const [profile, setProfile] = useState<UserProfile | null>(null)
	const [step, setStep] = useState<GateStep>(null)
	const [dismissed, setDismissed] = useState(false)

	const refreshProfile = async () => {
		const p = await getProfile()
		setProfile(p)
		return p
	}

	useEffect(() => {
		let active = true
		;(async () => {
			try {
				const p = await getProfile()
				if (!active) return
				setProfile(p)
			} catch {
				if (!active) return
				setProfile(null)
			} finally {
				if (!active) return
				setLoading(false)
			}
		})()
		return () => {
			active = false
		}
	}, [])

	useEffect(() => {
		if (loading || dismissed || !profile) {
			setStep(null)
			return
		}

		if (profile.link_prompt_dismissed) {
			setStep(null)
			return
		}

		if (shouldShowEmailPrompt(profile)) {
			setStep('email')
			return
		}

		if (shouldShowPasswordPrompt(profile)) {
			setStep('password')
			return
		}

		if (shouldShowTelegramPrompt(profile)) {
			setStep('telegram')
			return
		}

		setStep(null)
	}, [loading, dismissed, profile])

	const handleSnooze = async () => {
		try {
			await dismissLinkPrompt()
		} catch {
			// ignore
		}
		setDismissed(true)
		setStep(null)
		try {
			await refreshProfile()
		} catch {
			// ignore
		}
	}

	const title = useMemo(() => {
		if (step === 'email') return 'Давай сохраним твой путь'
		if (step === 'password') return 'Закрепим доступ'
		if (step === 'telegram') return 'Соединим приложение и Telegram'
		return ''
	}, [step])

	if (loading || !step) return null

	return (
		<div className="fixed inset-0 z-[60] flex items-end sm:items-center justify-center p-4 bg-black/60">
			<div
				className="w-full sm:max-w-md rounded-2xl border border-white/10 bg-white/10 backdrop-blur-xl text-white shadow-xl overflow-hidden">
				<div className="p-4 border-b border-white/10 flex items-start justify-between gap-3">
					<div>
						<p className="text-sm font-semibold">{title}</p>
						<p className="text-xs text-white/70 mt-1">Это займёт меньше минуты. И будет спокойнее
							дальше.</p>
					</div>
					<button
						type="button"
						onClick={handleSnooze}
						className="shrink-0 text-white/70 hover:text-white"
						aria-label="Закрыть"
					>
						<X className="w-5 h-5"/>
					</button>
				</div>

				<div className="p-4">
					{step === 'email' && (
						<EmailLinkPrompt onDone={handleSnooze}/>
					)}

					{step === 'password' && (
						<SetPasswordPrompt onDone={async () => {
							await refreshProfile()
							setStep(null)
						}} onSnooze={handleSnooze}/>
					)}

					{step === 'telegram' && (
						<TelegramLinkPrompt onSnooze={handleSnooze}/>
					)}
				</div>
			</div>
		</div>
	)
}

function EmailLinkPrompt({onDone}: { onDone: () => void }) {
	const [email, setEmail] = useState('')
	const [sending, setSending] = useState(false)
	const [sent, setSent] = useState(false)
	const [error, setError] = useState<string | null>(null)

	const handleSend = async () => {
		if (!email.includes('@')) {
			setError('Напиши email, чтобы я мог отправить письмо')
			return
		}

		const next = `${window.location.pathname}${window.location.search}`
		if (!sessionStorage.getItem('auth_next')) sessionStorage.setItem('auth_next', next)
		if (!localStorage.getItem('auth_next')) localStorage.setItem('auth_next', next)

		setSending(true)
		setError(null)
		try {
			await requestEmailLink(email)
			setSent(true)
		} catch (err: any) {
			setError(err?.response?.data?.detail || 'Не получилось отправить письмо. Давай попробуем ещё раз.')
		} finally {
			setSending(false)
		}
	}

	if (sent) {
		return (
			<div className="space-y-3">
				<div className="rounded-xl border border-emerald-600/30 bg-emerald-900/20 p-3">
					<p className="text-sm text-emerald-200">Письмо уже в пути: <strong>{email}</strong></p>
					<p className="text-xs text-emerald-200/70 mt-1">Открой почту и нажми на ссылку — так мы надёжно
						привяжем аккаунт.</p>
				</div>
				<Button variant="secondary" className="w-full" onClick={onDone}>
					Понятно, спасибо
				</Button>
			</div>
		)
	}

	return (
		<div className="space-y-3">
			<div className="flex items-center gap-2 text-sm text-white/90">
				<Mail className="w-4 h-4"/>
				<span>Укажи email — чтобы входить с любого устройства</span>
			</div>

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
					{sending ? <Loader2 className="w-4 h-4 animate-spin"/> : 'Отправить'}
				</Button>
			</div>

			{error && <p className="text-xs text-red-300">{error}</p>}

			<button
				type="button"
				onClick={onDone}
				className="text-xs text-white/60 hover:text-white"
			>
				Позже
			</button>
		</div>
	)
}

function SetPasswordPrompt({
							   onDone,
							   onSnooze,
						   }: {
	onDone: () => void
	onSnooze: () => void
}) {
	const [pw1, setPw1] = useState('')
	const [pw2, setPw2] = useState('')
	const [saving, setSaving] = useState(false)
	const [error, setError] = useState<string | null>(null)
	const [ok, setOk] = useState(false)

	const handleSave = async () => {
		if (pw1.length < 6) {
			setError('Пароль должен быть минимум 6 символов')
			return
		}
		if (pw1 !== pw2) {
			setError('Пароли не совпадают')
			return
		}

		setSaving(true)
		setError(null)
		try {
			await setPassword(pw1)
			setOk(true)
		} catch (err: any) {
			setError(err?.response?.data?.detail || 'Не получилось сохранить пароль. Давай попробуем ещё раз.')
		} finally {
			setSaving(false)
		}
	}

	if (ok) {
		return (
			<div className="space-y-3">
				<div className="rounded-xl border border-emerald-600/30 bg-emerald-900/20 p-3">
					<p className="text-sm text-emerald-200">Готово. Пароль установлен.</p>
					<p className="text-xs text-emerald-200/70 mt-1">Теперь можно спокойно входить из браузера и с разных
						устройств.</p>
				</div>
				<Button variant="secondary" className="w-full" onClick={onDone}>
					Продолжить
				</Button>
			</div>
		)
	}

	return (
		<div className="space-y-3">
			<div className="flex items-center gap-2 text-sm text-white/90">
				<Lock className="w-4 h-4"/>
				<span>У тебя уже есть email — осталось задать пароль</span>
			</div>

			<div className="space-y-2">
				<Input
					type="password"
					placeholder="Пароль"
					value={pw1}
					onChange={(e) => setPw1(e.target.value)}
				/>
				<Input
					type="password"
					placeholder="Повтори пароль"
					value={pw2}
					onChange={(e) => setPw2(e.target.value)}
				/>
			</div>

			{error && <p className="text-xs text-red-300">{error}</p>}

			<Button onClick={handleSave} disabled={saving} className="w-full">
				{saving ? <Loader2 className="w-4 h-4 animate-spin"/> : 'Сохранить пароль'}
			</Button>

			<button
				type="button"
				onClick={onSnooze}
				className="text-xs text-white/60 hover:text-white"
			>
				Позже
			</button>
		</div>
	)
}

function TelegramLinkPrompt({onSnooze}: { onSnooze: () => void }) {
	const [tgLink, setTgLink] = useState<TelegramLinkResponse | null>(null)
	const [loading, setLoading] = useState(false)
	const [error, setError] = useState<string | null>(null)
	const [timeLeft, setTimeLeft] = useState<number | null>(null)
	const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

	useEffect(() => {
		if (!tgLink?.expires_at) return

		const update = () => {
			const diff = Math.max(0, Math.floor((new Date(tgLink.expires_at!).getTime() - Date.now()) / 1000))
			setTimeLeft(diff)
			if (diff <= 0) {
				setTgLink(null)
				setTimeLeft(null)
			}
		}

		update()
		timerRef.current = setInterval(update, 1000)
		return () => {
			if (timerRef.current) clearInterval(timerRef.current)
		}
	}, [tgLink?.expires_at])

	const handleGenerate = async () => {
		setLoading(true)
		setError(null)
		try {
			const data = await generateTelegramLink()
			setTgLink(data)
		} catch (err: any) {
			setError(err?.response?.data?.detail || 'Не получилось подготовить ссылку. Давай попробуем ещё раз.')
		} finally {
			setLoading(false)
		}
	}

	const handleCopy = async () => {
		if (!tgLink?.token) return
		try {
			await navigator.clipboard.writeText(tgLink.token)
		} catch {
			// ignore
		}
	}

	return (
		<div className="space-y-3">
			<div className="flex items-center gap-2 text-sm text-white/90">
				<QrCode className="w-4 h-4"/>
				<span>Привяжи Telegram — чтобы бот и приложение работали вместе</span>
			</div>

			{!tgLink && (
				<Button onClick={handleGenerate} disabled={loading} className="w-full">
					{loading ? <Loader2 className="w-4 h-4 animate-spin"/> : 'Сгенерировать ссылку'}
				</Button>
			)}

			{tgLink?.deep_link && (
				<div className="space-y-3">
					<div className="rounded-xl border border-white/10 bg-white/5 p-3 space-y-2">
						<div className="flex items-center justify-between gap-3">
							<a
								href={tgLink.deep_link}
								target="_blank"
								rel="noreferrer"
								className="text-xs text-white/80 hover:text-white break-all flex items-start justify-center"
							>
								{tgLink.deep_link}
								<ExternalLink className="w-4 h-4"/>
							</a>
						</div>

						<div className="m-4 flex items-center justify-center">
							<img
								src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(tgLink.deep_link)}`}
								alt="QR"
								className="w-44 h-44"
							/>
						</div>

						<div className="flex items-center justify-between gap-2">
							<div className="text-xs text-white/70">Код: <span
								className="text-white">{tgLink.token}</span></div>
							<Button variant="glass" size="sm" onClick={handleCopy}>
								<Copy className="w-4 h-4"/>
								Копировать
							</Button>
						</div>

						{timeLeft !== null && (
							<div className="text-xs text-white/60">Ссылка активна ещё {timeLeft} сек.</div>
						)}
					</div>

					<div className="flex gap-2">
						<Button variant="glass" className="flex-1" onClick={handleGenerate} disabled={loading}>
							<RefreshCw className="w-4 h-4"/>
							Обновить
						</Button>
						<Button variant="glass" className="flex-1" onClick={onSnooze}>
							Позже
						</Button>
					</div>
				</div>
			)}

			{error && <p className="text-xs text-red-300">{error}</p>}

			{!tgLink && (
				<button
					type="button"
					onClick={onSnooze}
					className="text-xs text-white/60 hover:text-white"
				>
					Позже
				</button>
			)}
		</div>
	)
}
