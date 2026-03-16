import {useEffect, useState} from 'react'
import {
	getPracticesProgress, getPracticeRecommendations, startPracticeTracking,
	completePractice, pausePractice, resumePractice, hidePractice, resetPractice, deletePractice,
	getPractices, PracticeProgress, Practice, PracticeRecommendation
} from '../api/client'
import {
	Brain, Flame, Loader2, RefreshCw, Play, Target,
	Sparkles, Pause, Eye, RotateCcw, Trash2, MoreHorizontal, ChevronDown, BookOpen
} from 'lucide-react'
import {cn} from '@/lib/utils'
import {Button} from '@/components/ui/button'
import PageHeader from "@/components/ui/PageHeader.tsx";
import PracticeModal, {PracticeModalMode} from '@/components/practices/PracticeModal'
import PracticePreviewCard from '@/components/practices/PracticePreviewCard'
import PracticeProgressCard from '@/components/practices/PracticeProgressCard'
import {
	buildPracticeCatalogMap,
	practiceDetailsFromCatalog,
	practiceDetailsFromProgress,
	practiceDetailsFromRecommendation,
	PracticeDetails
} from '@/components/practices/practiceUtils'

export default function Practices() {
	const [loading, setLoading] = useState(true)
	const [actionLoading, setActionLoading] = useState<string | null>(null)
	const [progress, setProgress] = useState<PracticeProgress[]>([])
	const [recommendations, setRecommendations] = useState<PracticeRecommendation[]>([])
	const [menuOpen, setMenuOpen] = useState<string | null>(null)
	const [error, setError] = useState<string | null>(null)
	const [catalog, setCatalog] = useState<Practice[]>([])
	const [catalogSource, setCatalogSource] = useState<Practice[]>([])
	const [catalogMap, setCatalogMap] = useState<Record<string, Practice>>({})
	const [showCatalog, setShowCatalog] = useState(false)
	const [catalogLoading, setCatalogLoading] = useState(false)
	const [recsLoading, setRecsLoading] = useState(false)
	const [modalOpen, setModalOpen] = useState(false)
	const [modalMode, setModalMode] = useState<PracticeModalMode>('details')
	const [modalPractice, setModalPractice] = useState<PracticeDetails | null>(null)
	const [modalLoading, setModalLoading] = useState(false)

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

	const buildCatalogState = (practices: Practice[], progressList: PracticeProgress[]) => {
		const map = buildPracticeCatalogMap(practices)
		setCatalogSource(practices)
		setCatalogMap(map)
		const tracked = new Set(progressList.map(p => p.practice_id))
		setCatalog(practices.filter(p => !tracked.has(p.id)))
		return map
	}

	const ensureCatalogMap = async () => {
		if (Object.keys(catalogMap).length > 0) {
			return catalogMap
		}
		const data = await getPractices()
		return buildCatalogState(data.practices || [], progress)
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
		if (catalogSource.length > 0) { setShowCatalog(!showCatalog); return }
		setCatalogLoading(true)
		try {
			const data = await getPractices()
			buildCatalogState(data.practices || [], progress)
			setShowCatalog(true)
		} catch { setError('Не удалось загрузить каталог') }
		finally { setCatalogLoading(false) }
	}

	useEffect(() => { load() }, [])

	useEffect(() => {
		if (catalogSource.length === 0) {
			return
		}
		const tracked = new Set(progress.map(p => p.practice_id))
		setCatalog(catalogSource.filter(p => !tracked.has(p.id)))
	}, [progress, catalogSource])

	const habits = progress.filter(p => p.is_habit && !p.is_hidden)
	const active = progress.filter(p => !p.is_habit && p.is_active && !p.is_hidden)
	const paused = progress.filter(p => !p.is_active && !p.is_hidden)

	const handleOpenDetails = (details: PracticeDetails) => {
		setModalPractice(details)
		setModalMode('details')
		setModalOpen(true)
	}

	const handleOpenExecute = async (item: PracticeProgress) => {
		setModalLoading(true)
		try {
			const map = await ensureCatalogMap()
			const details = practiceDetailsFromProgress(item, map)
			setModalPractice(details)
			setModalMode('execute')
			setModalOpen(true)
		} catch {
			setError('Не удалось открыть практику')
		} finally {
			setModalLoading(false)
		}
	}

	const handleStartFromModal = async (practiceId: string) => {
		setModalLoading(true)
		try {
			await startPracticeTracking(practiceId)
			await load()
			setModalMode('execute')
		} catch {
			setError('Не удалось начать практику')
		} finally {
			setModalLoading(false)
		}
	}

	const handleCompleteFromModal = async (practiceId: string) => {
		setModalLoading(true)
		try {
			await completePractice(practiceId)
			await load()
			setModalOpen(false)
		} catch {
			setError('Не удалось отметить выполнение')
		} finally {
			setModalLoading(false)
		}
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

	const PracticeCard = ({p}: {p: PracticeProgress}) => (
		<PracticeProgressCard
			practice={p}
			isLoading={actionLoading === p.practice_id}
			onExecute={handleOpenExecute}
			menu={<PracticeMenu id={p.practice_id} isActive={p.is_active}/>}
		/>
	)

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
						<Button
							variant="ghost"
							size="sm"
							className="text-yellow-300/70 hover:text-yellow-300 text-xs"
							onClick={refreshRecommendations}
							disabled={recsLoading}
						>
							<RefreshCw className={cn("h-3.5 w-3.5 mr-1", recsLoading && "animate-spin")}/>
							Обновить подбор
						</Button>
					</div>
					<div className="grid grid-cols-1 md:grid-cols-2 gap-3">
						{recommendations.map((r, idx) => (
							<PracticePreviewCard
								key={`rec-${r.id || idx}`}
								practice={practiceDetailsFromRecommendation(r)}
								variant="highlight"
								onClick={() => handleOpenDetails(practiceDetailsFromRecommendation(r))}
							/>
						))}
					</div>
				</section>
			)}

			{/* Catalog button + lazy catalog */}
			<section>
				<Button
					variant="outline"
					className="w-full border-white/20 text-white/70 hover:bg-white/10 hover:text-white"
					onClick={loadCatalog}
					disabled={catalogLoading}
				>
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
							<PracticePreviewCard
								key={`cat-${p.id}`}
								practice={practiceDetailsFromCatalog(p)}
								onClick={() => handleOpenDetails(practiceDetailsFromCatalog(p))}
							/>
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
