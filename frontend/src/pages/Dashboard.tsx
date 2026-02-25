import {useEffect, useState} from 'react'
import {getDailyQuote, getDailyActions, toggleDailyAction} from '../api/client'
import {useTelegram} from '../hooks/useTelegram'
import {Link} from 'react-router-dom'
import {Quote, Coffee, Check, Target, Sparkles, Loader2} from 'lucide-react'
import {cn} from '@/lib/utils'
import {Card, CardContent} from '@/components/ui/card'
import {Button} from '@/components/ui/button'

interface DailyAction {
	id: string
	partner_name: string
	description: string
	why: string
	completed: boolean
}

interface QuoteData {
	text: string
	author?: string
	context: string
}

export default function Dashboard() {
	const {user} = useTelegram()
	const [quote, setQuote] = useState<QuoteData | null>(null)
	const [actions, setActions] = useState<DailyAction[]>([])
	const [loading, setLoading] = useState(false)
	const [initialLoading, setInitialLoading] = useState(true)

	const fetchData = async () => {
		try {
			const [quoteData, actionsData] = await Promise.all([
				getDailyQuote(),
				getDailyActions()
			])
			setQuote(quoteData)
			setActions(actionsData.actions)
		} catch (error) {
			console.error('Error fetching dashboard data:', error)
		} finally {
			setInitialLoading(false)
		}
	}

	useEffect(() => {
		fetchData()
	}, [])

	const handleToggleAction = async (id: string, currentStatus: boolean) => {
		try {
			setLoading(true)
			await toggleDailyAction(id, !currentStatus)
			// Update local state for immediate feedback
			setActions(prev => prev.map(a =>
				a.id === id ? {...a, completed: !currentStatus} : a
			))
		} catch (error) {
			console.error('Failed to toggle action:', error)
		} finally {
			setLoading(false)
		}
	}

	if (initialLoading) {
		return (
			<div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
				<Loader2 className="h-8 w-8 animate-spin text-primary"/>
				<p className=" text-sm">Загружаем твой день...</p>
			</div>
		)
	}

	return (
		<div className="flex flex-col gap-6 p-4 max-w-5xl mx-auto w-full">
			{/* Header */}
			<div className="space-y-1 mt-2">
				<h1 className="text-3xl font-bold tracking-tight text-white">
					Привет, {user?.first_name || 'друг'}!
				</h1>
				<p className="">Твой путь к осознанности начинается здесь.</p>
			</div>

			<div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
				{/* Quote Card */}
				<div className="lg:col-span-2">
					{quote && (
						<Card className="h-full shadow-soft relative flex flex-col justify-center">
							<div className="absolute top-0 right-0 p-4 opacity-5">
								<Quote className="h-24 w-24"/>
							</div>
							<CardContent className="p-6 relative z-10">
								<Quote className="h-6 w-6 text-white mb-3 opacity-80"/>
								<p className="text-lg md:text-xl font-medium italic leading-relaxed text-white mb-4">
									"{quote.text}"
								</p>
								<div className="flex justify-between items-end">
                  <span className="text-sm font-semibold text-white/50">
                    {quote.author || 'Аноним'}
                  </span>
									<span className="text-[10px] uppercase tracking-wider font-medium text-white/50">
                    {quote.context}
                  </span>
								</div>
							</CardContent>
						</Card>
					)}
				</div>

				{/* Quick Actions / Stats Placeholder or Coffee Meditation CTA */}
				<div className="flex flex-col justify-center gap-4">
					<Card
						className="bg-gradient-to-br from-orange-100/80 to-rose-100/80 border-white/40 shadow-sm h-full backdrop-blur-md">
						<CardContent className="p-6 flex flex-col items-center justify-center text-center h-full gap-4">
							<div className="p-3 bg-white/70 rounded-full shadow-sm">
								<Coffee className="h-8 w-8 text-orange-500"/>
							</div>
							<div>
								<h3 className="font-semibold text-primary">Кофе-медитация</h3>
								<p className="text-xs mt-1 text-primary/80">Заряди свои семена силой радости</p>
							</div>
							<Button
								variant="default"
								className="w-full rounded-full bg-gradient-to-r from-orange-400 to-rose-500 hover:from-orange-500 hover:to-rose-600 border-0 text-white"
								asChild
							>
								<Link to="/meditation">
									Начать
								</Link>
							</Button>
						</CardContent>
					</Card>
				</div>
			</div>

			{/* Daily Actions Header */}
			<div className="flex items-center justify-between mt-2">
				<div className="flex items-center gap-2 text-white">
					<Target className="h-5 w-5"/>
					<h2 className="text-xl font-semibold">4 действия на сегодня</h2>
				</div>
			</div>

			{/* Actions List */}
			<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
				{actions.length === 0 ? (
					<div
						className="col-span-full text-center py-12 px-4 rounded-xl border border-dashed border-muted-foreground/20 bg-white/20 backdrop-blur-main">
						<Sparkles className="h-8 w-8  mx-auto mb-3 opacity-50"/>
						<p className="">
							Сейчас у тебя нет активного кармического проекта или плана на день.
						</p>
						<p className="text-xs mt-2 opacity-80">
							Загляни в раздел <span className="font-semibold">«Проблема»</span>, опиши свою ситуацию и вместе мы
								соберём для тебя понятный, добрый план действий.
						</p>
						<div className="mt-4 flex justify-center">
							<Button
								variant="outline"
								className="rounded-full px-6"
								asChild
							>
								<Link to="/problem">Перейти к главной задаче</Link>
							</Button>
						</div>
					</div>
				) : (
					actions.map((action) => (
						<div
							key={action.id}
							onClick={() => handleToggleAction(action.id, action.completed)}
							className={cn(
								"group relative overflow-hidden rounded-2xl border p-5 transition-all duration-300 cursor-pointer h-full backdrop-blur-main",
								action.completed
									? "bg-white/30 shadow-none"
									: "bg-white/10 hover:bg-white/20 border-white/30 shadow-sm hover:shadow-md hover:border-white/60",
								loading && "opacity-70 pointer-events-none"
							)}
						>
							<div className="flex items-start gap-4 relative z-10 h-full">
								{/* Checkbox */}
								<div className={cn(
									"flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 transition-all duration-300 mt-0.5",
									action.completed
										? "border-primary/80 bg-primary text-white"
										: "border-muted-foreground/30 bg-white/90 group-hover:border-primary"
								)}>
									<Check
										className={cn("h-3.5 w-3.5", action.completed ? "opacity-100" : "opacity-0")}/>
								</div>

								{/* Content */}
								<div className="flex-1 space-y-2">
									<p className={cn(
										"text-xs font-semibold transition-colors",
										action.completed ? "line-through decoration-muted-foreground/50" : "text-white/60"
									)}>
										{action.partner_name}
									</p>
									<p className={cn(
										"text-base leading-relaxed transition-all",
										action.completed ? " line-through decoration-muted-foreground/50" : "text-white"
									)}>
										{action.description}
									</p>
									<div className="flex items-center gap-1.5 pt-1">
										<Target className="h-3 w-3 text-white/60"/>
										<span className="text-xs italic">{action.why}</span>
									</div>
								</div>

								{/* Seed Action Button */}
								{action.completed && (
									<Button
										size="icon"
										variant="secondary"
										className="h-8 w-8 rounded-full  shadow-sm hover:bg-primary hover:text-primary-foreground absolute right-1 bottom-1 animate-in fade-in zoom-in duration-300"
										asChild
										onClick={(e) => e.stopPropagation()}
									>
										<Link to={`/journal?description=${encodeURIComponent(action.description)}`}>
											<Sparkles className="h-4 w-4"/>
										</Link>
									</Button>
								)}
							</div>
						</div>
					))
				)}
			</div>
		</div>
	)
}
