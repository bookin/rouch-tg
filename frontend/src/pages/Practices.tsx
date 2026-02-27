import {useEffect, useState} from 'react'
import {
	getPracticesProgress, getPracticeRecommendations, startPracticeTracking,
	completePractice, pausePractice, resumePractice, hidePractice, resetPractice, deletePractice,
	getPractices, PracticeProgress, Practice
} from '../api/client'
import {
	Brain, Clock, Flame, Loader2, RefreshCw, Play, Plus, Target, TrendingUp,
	Sparkles, Pause, Eye, RotateCcw, Trash2, MoreHorizontal, ChevronDown, BookOpen
} from 'lucide-react'
import {cn} from '@/lib/utils'
import {Card} from '@/components/ui/card'
import {Button} from '@/components/ui/button'
import PageHeader from "@/components/ui/PageHeader.tsx";

interface RecommendationItem {
	id: string
	name: string
	category: string
	content: string
	duration: number
	benefits?: string
	tags?: string[]
}

export default function Practices() {
	const [loading, setLoading] = useState(true)
	const [actionLoading, setActionLoading] = useState<string | null>(null)
	const [progress, setProgress] = useState<PracticeProgress[]>([])
	const [recommendations, setRecommendations] = useState<RecommendationItem[]>([])
	const [menuOpen, setMenuOpen] = useState<string | null>(null)
	const [error, setError] = useState<string | null>(null)
	const [catalog, setCatalog] = useState<Practice[]>([])
	const [showCatalog, setShowCatalog] = useState(false)
	const [catalogLoading, setCatalogLoading] = useState(false)
	const [recsLoading, setRecsLoading] = useState(false)

	const load = async () => {
		try {
			setError(null)
			setLoading(true)
			const [progressData, recData] = await Promise.all([
				getPracticesProgress(),
				getPracticeRecommendations()
			])
			setProgress(progressData.progress || [])
			setRecommendations(recData.recommendations || [])
		} catch (e: any) {
			setError(e?.message || 'Не удалось загрузить данные')
		} finally {
			setLoading(false)
		}
	}

	const refreshRecommendations = async () => {
		setRecsLoading(true)
		try {
			const recData = await getPracticeRecommendations()
			setRecommendations(recData.recommendations || [])
		} catch { /* ignore */ }
		finally { setRecsLoading(false) }
	}

	const loadCatalog = async () => {
		if (catalog.length > 0) { setShowCatalog(!showCatalog); return }
		setCatalogLoading(true)
		try {
			const data = await getPractices()
			const tracked = new Set(progress.map(p => p.practice_id))
			setCatalog((data.practices || []).filter((p: Practice) => !tracked.has(p.id)))
			setShowCatalog(true)
		} catch { setError('Не удалось загрузить каталог') }
		finally { setCatalogLoading(false) }
	}

	useEffect(() => { load() }, [])

	const habits = progress.filter(p => p.is_habit && !p.is_hidden)
	const active = progress.filter(p => !p.is_habit && p.is_active && !p.is_hidden)
	const paused = progress.filter(p => !p.is_active && !p.is_hidden)

	const handleStart = async (id: string) => {
		setActionLoading(id)
		try { await startPracticeTracking(id); await load() }
		catch { setError('Не удалось начать практику') }
		finally { setActionLoading(null) }
	}

	const handleComplete = async (id: string) => {
		setActionLoading(id)
		try { await completePractice(id); await load() }
		catch { setError('Не удалось отметить выполнение') }
		finally { setActionLoading(null) }
	}

	const handleAction = async (action: string, id: string) => {
		setMenuOpen(null)
		setActionLoading(id)
		try {
			if (action === 'pause') await pausePractice(id)
			else if (action === 'resume') await resumePractice(id)
			else if (action === 'hide') await hidePractice(id)
			else if (action === 'reset') await resetPractice(id)
			else if (action === 'delete') {
				if (!window.confirm('Удалить практику и все связанные семена? Это действие необратимо.')) {
					setActionLoading(null)
					return
				}
				await deletePractice(id)
			}
			await load()
		} catch { setError('Не удалось выполнить действие') }
		finally { setActionLoading(null) }
	}

	if (loading && progress.length === 0) {
		return (
			<div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
				<Loader2 className="h-8 w-8 animate-spin text-primary"/>
				<p className="text-sm">Загружаем практики...</p>
			</div>
		)
	}

	const ProgressBar = ({score, minScore}: {score: number; minScore: number}) => (
		<div className="w-full h-1.5 bg-white/20 rounded-full overflow-hidden">
			<div
				className="h-full bg-gradient-to-r from-blue-400 to-green-400 transition-all duration-300"
				style={{width: `${Math.min(100, (score / minScore) * 100)}%`}}
			/>
		</div>
	)

	const PracticeMenu = ({id, isActive}: {id: string; isActive: boolean}) => (
		<div className="relative">
			<Button variant="ghost" size="icon" className="h-7 w-7 text-white/60"
				onClick={(e) => { e.stopPropagation(); setMenuOpen(menuOpen === id ? null : id) }}>
				<MoreHorizontal className="h-4 w-4"/>
			</Button>
			{menuOpen === id && (
				<div className="absolute right-0 top-8 z-50 bg-zinc-900 border border-white/20 rounded-lg shadow-xl py-1 min-w-[180px]"
					onClick={e => e.stopPropagation()}>
					{isActive ? (
						<button className="w-full text-left px-3 py-2 text-sm text-white/80 hover:bg-white/10 flex items-center gap-2"
							onClick={() => handleAction('pause', id)}>
							<Pause className="h-3.5 w-3.5"/> Приостановить
						</button>
					) : (
						<button className="w-full text-left px-3 py-2 text-sm text-white/80 hover:bg-white/10 flex items-center gap-2"
							onClick={() => handleAction('resume', id)}>
							<Play className="h-3.5 w-3.5"/> Возобновить
						</button>
					)}
					<button className="w-full text-left px-3 py-2 text-sm text-white/80 hover:bg-white/10 flex items-center gap-2"
						onClick={() => handleAction('hide', id)}>
						<Eye className="h-3.5 w-3.5"/> Скрыть
					</button>
					<button className="w-full text-left px-3 py-2 text-sm text-white/80 hover:bg-white/10 flex items-center gap-2"
						onClick={() => handleAction('reset', id)}>
						<RotateCcw className="h-3.5 w-3.5"/> Сбросить прогресс
					</button>
					<button className="w-full text-left px-3 py-2 text-sm text-red-400 hover:bg-red-500/10 flex items-center gap-2"
						onClick={() => handleAction('delete', id)}>
						<Trash2 className="h-3.5 w-3.5"/> Удалить всё
					</button>
				</div>
			)}
		</div>
	)

	const PracticeCard = ({p}: {p: PracticeProgress}) => {
		const isLoading = actionLoading === p.practice_id
		return (
			<Card className={cn(
				"group relative overflow-hidden rounded-2xl border p-4 transition-all duration-300 backdrop-blur-main",
				p.is_habit
					? "bg-green-500/15 border-green-400/30"
					: !p.is_active
					? "bg-white/5 border-white/10 opacity-60"
					: "bg-white/10 border-white/20",
				isLoading && "opacity-70 pointer-events-none"
			)}>
				<div className="flex items-start justify-between mb-2">
					<div className="flex items-center gap-2 min-w-0 flex-1">
						<span className="text-lg">{p.is_habit ? "🌿" : "🧘"}</span>
						<h3 className="font-semibold text-white text-sm truncate">{p.practice_name}</h3>
					</div>
					<div className="flex items-center gap-1 flex-shrink-0">
						<span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-white/10 text-white/50">
							{p.practice_category}
						</span>
						<PracticeMenu id={p.practice_id} isActive={p.is_active}/>
					</div>
				</div>

				{/* Stats */}
				<div className="flex items-center gap-3 text-xs text-white/70 mb-2">
					{p.streak_days > 0 && (
						<span className="flex items-center gap-1">
							<Flame className="h-3 w-3 text-orange-300"/>
							{p.streak_days} дн.
						</span>
					)}
					{p.habit_score > 0 && (
						<span className="flex items-center gap-1">
							<TrendingUp className="h-3 w-3 text-blue-300"/>
							{p.habit_score}%
						</span>
					)}
					<span className="flex items-center gap-1">
						<Clock className="h-3 w-3"/>
						{p.practice_duration} мин
					</span>
				</div>

				{/* Habit progress bar */}
				{!p.is_habit && p.habit_score > 0 && (
					<div className="mb-3">
						<ProgressBar score={p.habit_score} minScore={p.habit_min_score}/>
						<p className="text-[10px] text-white/40 mt-1">
							До привычки: {p.habit_score}/{p.habit_min_score}% · {p.streak_days}/{p.habit_min_streak_days} дн.
						</p>
					</div>
				)}

				{p.is_habit && (
					<p className="text-xs text-green-300 font-medium mb-2">✅ Сформированная привычка</p>
				)}

				{!p.is_active && (
					<p className="text-xs text-yellow-300/70 font-medium mb-2">⏸ На паузе</p>
				)}

				{/* Action button */}
				{p.is_active && p.can_complete_today && !p.is_habit && (
					<Button size="sm" className="w-full mt-1" onClick={() => handleComplete(p.practice_id)}>
						{isLoading ? <Loader2 className="h-3.5 w-3.5 mr-2 animate-spin"/> : <Play className="h-3.5 w-3.5 mr-2"/>}
						Выполнить
					</Button>
				)}
			</Card>
		)
	}

	return (
		<div className="flex flex-col gap-6 p-4 max-w-5xl mx-auto w-full pb-24" onClick={() => setMenuOpen(null)}>
			<div className="space-y-1 mt-2 flex items-center justify-between">
				<div>
					<PageHeader text="Практики" icon={Brain}/>
					<p className="leading-relaxed text-sm mt-1">Твой путь к осознанным привычкам</p>
				</div>
				<Button variant="ghost" size="icon" onClick={load} disabled={loading}>
					<RefreshCw className={cn("h-5 w-5", loading && "animate-spin")}/>
				</Button>
			</div>

			{error && (
				<div className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm font-medium border border-destructive/20">
					{error}
				</div>
			)}

			{/* Formed Habits */}
			{habits.length > 0 && (
				<section>
					<h2 className="text-lg font-semibold flex items-center gap-2 text-white mb-3">
						<Target className="h-5 w-5 text-green-400"/> Сформированные привычки
					</h2>
					<div className="grid grid-cols-1 md:grid-cols-2 gap-3">
						{habits.map(p => <PracticeCard key={p.practice_id} p={p}/>)}
					</div>
				</section>
			)}

			{/* Active Practices */}
			{active.length > 0 && (
				<section>
					<h2 className="text-lg font-semibold flex items-center gap-2 text-white mb-3">
						<Flame className="h-5 w-5 text-orange-400"/> Активные практики
					</h2>
					<div className="grid grid-cols-1 md:grid-cols-2 gap-3">
						{active.map(p => <PracticeCard key={p.practice_id} p={p}/>)}
					</div>
				</section>
			)}

			{/* Paused */}
			{paused.length > 0 && (
				<section>
					<h2 className="text-sm font-semibold flex items-center gap-2 text-white/50 mb-2">
						<Pause className="h-4 w-4"/> На паузе
					</h2>
					<div className="grid grid-cols-1 md:grid-cols-2 gap-3">
						{paused.map(p => <PracticeCard key={p.practice_id} p={p}/>)}
					</div>
				</section>
			)}

			{/* AI Recommendations */}
			{recommendations.length > 0 && (
				<section>
					<div className="flex items-center justify-between mb-3">
						<h2 className="text-lg font-semibold flex items-center gap-2 text-white">
							<Sparkles className="h-5 w-5 text-yellow-300"/> Рекомендации для тебя
						</h2>
						<Button variant="ghost" size="sm" className="text-yellow-300/70 hover:text-yellow-300 text-xs"
							onClick={refreshRecommendations} disabled={recsLoading}>
							<RefreshCw className={cn("h-3.5 w-3.5 mr-1", recsLoading && "animate-spin")}/>
							Обновить подбор
						</Button>
					</div>
					<div className="grid grid-cols-1 md:grid-cols-2 gap-3">
						{recommendations.map((r, idx) => (
							<Card key={`rec-${r.id || idx}`}
								className="border border-yellow-500/20 bg-yellow-500/5 backdrop-blur-main rounded-2xl p-4">
								<div className="flex items-start justify-between mb-2">
									<h3 className="font-semibold text-white text-sm">{r.name}</h3>
									<span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-yellow-500/20 text-yellow-300">
										{r.category}
									</span>
								</div>
								<div className="flex items-center gap-2 text-xs text-white/60 mb-2">
									<Clock className="h-3 w-3"/>{r.duration} мин
								</div>
								{r.benefits && (
									<p className="text-xs text-white/50 mb-3 line-clamp-2">{r.benefits}</p>
								)}
								{r.tags && r.tags.length > 0 && (
									<div className="flex flex-wrap gap-1 mb-3">
										{r.tags.slice(0, 4).map(t => (
											<span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-white/40">{t}</span>
										))}
									</div>
								)}
								<Button size="sm" className="w-full bg-yellow-500 hover:bg-yellow-600 text-white"
									onClick={() => handleStart(r.id)}
									disabled={actionLoading === r.id}>
									{actionLoading === r.id
										? <Loader2 className="h-3.5 w-3.5 mr-2 animate-spin"/>
										: <Plus className="h-3.5 w-3.5 mr-2"/>
									}
									Начать практику
								</Button>
							</Card>
						))}
					</div>
				</section>
			)}

			{/* Catalog button + lazy catalog */}
			<section>
				<Button variant="outline" className="w-full border-white/20 text-white/70 hover:bg-white/10"
					onClick={loadCatalog} disabled={catalogLoading}>
					{catalogLoading
						? <Loader2 className="h-4 w-4 mr-2 animate-spin"/>
						: <BookOpen className="h-4 w-4 mr-2"/>
					}
					{showCatalog ? 'Скрыть каталог' : 'Все практики'}
					<ChevronDown className={cn("h-4 w-4 ml-auto transition-transform", showCatalog && "rotate-180")}/>
				</Button>

				{showCatalog && catalog.length > 0 && (
					<div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
						{catalog.map(p => (
							<Card key={`cat-${p.id}`}
								className="border border-white/10 bg-white/5 backdrop-blur-main rounded-2xl p-4">
								<div className="flex items-start justify-between mb-2">
									<h3 className="font-semibold text-white text-sm">{p.name}</h3>
									<span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-white/10 text-white/40">
										{p.category}
									</span>
								</div>
								<div className="flex items-center gap-2 text-xs text-white/50 mb-2">
									<Clock className="h-3 w-3"/>{p.duration} мин
								</div>
								{p.benefits && <p className="text-xs text-white/40 mb-3 line-clamp-2">{p.benefits}</p>}
								<Button size="sm" className="w-full" variant="outline"
									onClick={() => handleStart(p.id)} disabled={actionLoading === p.id}>
									{actionLoading === p.id
										? <Loader2 className="h-3.5 w-3.5 mr-2 animate-spin"/>
										: <Plus className="h-3.5 w-3.5 mr-2"/>
									}
									Начать практику
								</Button>
							</Card>
						))}
					</div>
				)}
				{showCatalog && catalog.length === 0 && !catalogLoading && (
					<p className="text-center text-white/40 text-sm mt-3">Все практики уже добавлены</p>
				)}
			</section>

			{/* Empty state */}
			{progress.length === 0 && recommendations.length === 0 && !loading && (
				<div className="text-center py-12 px-4 rounded-xl border border-dashed border-white/20 bg-white/5">
					<Sparkles className="h-8 w-8 mx-auto mb-3 text-white/30"/>
					<p className="text-white/60 text-sm">
						Пока нет практик. Скоро здесь появятся рекомендации, подобранные специально для тебя.
					</p>
				</div>
			)}
		</div>
	)
}
