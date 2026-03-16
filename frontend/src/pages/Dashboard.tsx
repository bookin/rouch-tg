import {useEffect, useState} from 'react'
import {
	getDailyQuote,
	getDailyActions,
	toggleDailyAction,
	getPracticesProgress,
	completePractice,
	getPracticeRecommendations,
	startPracticeTracking,
	getPractices,
	PracticeProgress,
	Practice,
	PracticeRecommendation,
	getActiveProject
} from '../api/client'
import {useTelegram} from '../hooks/useTelegram'
import {Link} from 'react-router-dom'
import {Quote, Coffee, Check, Target, Sparkles, Loader2, Flame, ArrowRight} from 'lucide-react'
import {cn} from '@/lib/utils'
import {Card, CardContent} from '@/components/ui/card'
import {Button} from '@/components/ui/button'
import PracticeModal, {PracticeModalMode} from '@/components/practices/PracticeModal'
import PracticePreviewCard from '@/components/practices/PracticePreviewCard'
import PracticeProgressCard from '@/components/practices/PracticeProgressCard'
import {
	buildPracticeCatalogMap,
	practiceDetailsFromProgress,
	practiceDetailsFromRecommendation,
	PracticeDetails
} from '@/components/practices/practiceUtils'

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
	const [practices, setPractices] = useState<PracticeProgress[]>([])
	const [recommendations, setRecommendations] = useState<PracticeRecommendation[]>([])
	const [loading, setLoading] = useState(false)
	const [initialLoading, setInitialLoading] = useState(true)
	const [hasActiveProject, setHasActiveProject] = useState(false)
	const [catalogMap, setCatalogMap] = useState<Record<string, Practice>>({})
	const [modalOpen, setModalOpen] = useState(false)
	const [modalMode, setModalMode] = useState<PracticeModalMode>('details')
	const [modalPractice, setModalPractice] = useState<PracticeDetails | null>(null)
	const [modalLoading, setModalLoading] = useState(false)

	// Filter: only visible active/habit practices
	const visiblePractices = practices.filter(p => !p.is_hidden && (p.is_active || p.is_habit))
	const isEmpty = visiblePractices.length === 0

	const ensureCatalogMap = async () => {
		if (Object.keys(catalogMap).length > 0) {
			return catalogMap
		}
		const data = await getPractices()
		const map = buildPracticeCatalogMap(data.practices || [])
		setCatalogMap(map)
		return map
	}

	const handleOpenDetails = (details: PracticeDetails) => {
		setModalPractice(details)
		setModalMode('details')
		setModalOpen(true)
	}

	const handleOpenExecute = async (practice: PracticeProgress) => {
		setModalLoading(true)
		try {
			const map = await ensureCatalogMap()
			const details = practiceDetailsFromProgress(practice, map)
			setModalPractice(details)
			setModalMode('execute')
			setModalOpen(true)
		} catch (error) {
			console.error('Error opening practice:', error)
		} finally {
			setModalLoading(false)
		}
	}

	const handleStartFromModal = async (practiceId: string) => {
		setModalLoading(true)
		try {
			await startPracticeTracking(practiceId)
			const practicesData = await getPracticesProgress()
			setPractices(practicesData.progress || [])
			setRecommendations(prev => prev.filter(r => r.id !== practiceId))
			setModalMode('execute')
		} catch (error) {
			console.error('Error starting practice:', error)
		} finally {
			setModalLoading(false)
		}
	}

	const handleCompleteFromModal = async (practiceId: string) => {
		setModalLoading(true)
		try {
			await completePractice(practiceId)
			const practicesData = await getPracticesProgress()
			setPractices(practicesData.progress || [])
			setModalOpen(false)
		} catch (error) {
			console.error('Error completing practice:', error)
		} finally {
			setModalLoading(false)
		}
	}

	const fetchData = async () => {
		try {
			const [quoteData, actionsData, practicesData, projectData] = await Promise.all([
				getDailyQuote(),
				getDailyActions(),
				getPracticesProgress(),
				getActiveProject()
			])
			setQuote(quoteData)
			setActions(actionsData.actions)
			const progressList = practicesData.progress || []
			setPractices(progressList)
			setHasActiveProject(Boolean(projectData?.has_active_project))

			// If no visible practices — fetch recommendations
			const visible = progressList.filter((p: PracticeProgress) => !p.is_hidden && (p.is_active || p.is_habit))
			if (visible.length === 0) {
				try {
					const recData = await getPracticeRecommendations()
					setRecommendations(recData.recommendations || [])
				} catch { /* ignore */ }
			}
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
					{hasActiveProject ? (
						<Card
							className="bg-gradient-to-br from-orange-100/80 to-rose-100/80 border-white/40 shadow-sm h-full backdrop-blur-md">
							<CardContent className="p-6 flex flex-col items-center justify-center text-center h-full gap-4">
								<div className="p-3 bg-white/70 rounded-full shadow-sm">
									<Coffee className="h-8 w-8 text-orange-500"/>
								</div>
								<div>
									<h3 className="font-semibold text-primary">Кофе-медитация</h3>
									<p className="text-xs mt-1 text-primary/80">Усиль семена через радость и посвяти результат</p>
								</div>
								<Button
									variant="default"
									className="w-full rounded-full bg-gradient-to-r from-orange-400 to-rose-500 hover:from-orange-500 hover:to-rose-600 border-0 text-white"
									asChild
								>
									<Link to="/coffee">
										Начать
									</Link>
								</Button>
							</CardContent>
						</Card>
					) : (
						<Card
							className="bg-gradient-to-br from-white/20 to-white/10 border-white/20 shadow-sm h-full backdrop-blur-md">
							<CardContent className="p-6 flex flex-col items-center justify-center text-center h-full gap-4">
								<div className="p-3 bg-white/10 rounded-full shadow-sm border border-white/20">
									<Coffee className="h-8 w-8 text-white"/>
								</div>
								<div>
									<h3 className="font-semibold text-white">Твой проект — это опора</h3>
									<p className="text-xs mt-1 text-white/80">Соберём его спокойно — и день станет понятнее</p>
								</div>
								<Button
									variant="outline"
									className="w-full rounded-full"
									asChild
								>
									<Link to="/problem">
										Собрать проект
									</Link>
								</Button>
							</CardContent>
						</Card>
					)}
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

			{/* Practices Header */}
			{visiblePractices.length > 0 && (
				<div className="flex items-center justify-between mt-6">
					<div className="flex items-center gap-2 text-white">
						<Flame className="h-5 w-5"/>
						<h2 className="text-xl font-semibold">Твои практики</h2>
					</div>
					<Button
						variant="outline"
						className="rounded-full px-4 text-xs border-white/30 text-white hover:bg-white/10 hover:text-white"
						asChild
					>
						<Link to="/practices">Все практики</Link>
					</Button>
				</div>
			)}

			{/* Dashboard Recommendations (when no practices) */}
			{isEmpty && recommendations.length > 0 && (
				<>
					<div className="flex items-center justify-between mt-6">
						<div className="flex items-center gap-2 text-white">
							<Sparkles className="h-5 w-5 text-yellow-300"/>
							<h2 className="text-xl font-semibold">Практики для тебя</h2>
						</div>
					</div>
					<div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
						{recommendations.slice(0, 4).map((r) => (
							<PracticePreviewCard
								key={`rec-${r.id}`}
								practice={practiceDetailsFromRecommendation(r)}
								variant="highlight"
								onClick={() => handleOpenDetails(practiceDetailsFromRecommendation(r))}
							/>
						))}
					</div>
				</>
			)}

			{/* Practices List */}
			{visiblePractices.length > 0 && (
				<div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
					{visiblePractices.slice(0, 4).map((practice) => (
						<PracticeProgressCard
							key={practice.practice_id}
							practice={practice}
							onExecute={handleOpenExecute}
							showDuration={false}
						/>
					))}
				</div>
			)}

			{/* CTA when has practices */}
			{!isEmpty && (
				<div className="mt-2">
					<Button variant="outline" className="w-full rounded-full border-white/20 text-white/60 hover:bg-white/10 text-xs hover:text-white" asChild>
						<Link to="/practices">
							<Sparkles className="h-3.5 w-3.5 mr-2 text-yellow-300"/>
							Хочу новые практики
							<ArrowRight className="h-3.5 w-3.5 ml-auto"/>
						</Link>
					</Button>
				</div>
			)}

			<PracticeModal
				open={modalOpen}
				mode={modalMode}
				practice={modalPractice}
				onClose={() => setModalOpen(false)}
				onStart={handleStartFromModal}
				onComplete={handleCompleteFromModal}
				isLoading={modalLoading}
			/>
		</div>
	)
}
