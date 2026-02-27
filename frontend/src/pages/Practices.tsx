import {useEffect, useState} from 'react'
import {useNavigate} from 'react-router-dom'
import {getHabits, getPractices, startPracticeTracking, completePractice, getPracticesProgress, getPracticeRecommendations, PracticeProgress} from '../api/client'
import {Brain, CalendarDays, Clock, Dumbbell, Flame, Loader2, RefreshCw, Repeat, Play, Plus, Target, TrendingUp, Sparkles} from 'lucide-react'
import {cn} from '@/lib/utils'
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card'
import {Button} from '@/components/ui/button'
import PageHeader from "@/components/ui/PageHeader.tsx";

interface PracticeItem {
	id?: string  // ID из Qdrant metadata
	name: string
	category: string
	content: string
	duration: number
	score?: number
}

interface HabitItem {
	id: string
	practice_id: string
	frequency: string
	preferred_time: string
	duration: number
	is_active: boolean
}

export default function Practices() {
	const navigate = useNavigate()
	const [loading, setLoading] = useState(true)
	const [practices, setPractices] = useState<PracticeItem[]>([])
	const [habits, setHabits] = useState<HabitItem[]>([])
	const [progressMap, setProgressMap] = useState<Record<string, PracticeProgress>>({})
	const [recommendations, setRecommendations] = useState<PracticeItem[]>([])
	const [error, setError] = useState<string | null>(null)

	const load = async () => {
		try {
			setError(null)
			setLoading(true)

			const [practicesData, habitsData, progressData, recommendationsData] = await Promise.all([
				getPractices(),
				getHabits(),
				getPracticesProgress(),
				getPracticeRecommendations()
			])

			setPractices(practicesData.practices || [])
			setHabits(habitsData.habits || [])
			setRecommendations(recommendationsData.recommendations || [])
			
			// Create progress map for easy lookup
			const progressRecord: Record<string, PracticeProgress> = {}
			progressData.progress.forEach(p => {
				progressRecord[p.practice_id] = p
			})
			setProgressMap(progressRecord)
		} catch (e: any) {
			setError(e?.message || 'Failed to load practices')
		} finally {
			setLoading(false)
		}
	}

	const startPractice = async (practiceId: string) => {
		try {
			console.log('Starting practice with ID:', practiceId)
			console.log('Available practices:', practices.map(p => ({ name: p.name, id: p.id })))
			
			const response = await startPracticeTracking(practiceId)
			console.log('Full API response:', response)
			console.log('Response status:', response.status)
			console.log('Response data:', response.data)
			
			const result = response.data || response
			console.log('Start practice result:', result)
			load() // Reload to get updated progress
		} catch (e: any) {
			console.error('Start practice error:', e)
			console.error('Error response:', e.response?.data)
			setError(e?.message || 'Failed to start practice')
		}
	}

	const completePracticeSession = async (practiceId: string) => {
		try {
			console.log('Completing practice with ID:', practiceId)
			const result = await completePractice(practiceId)
			console.log('Complete practice result:', result)
			load() // Reload to get updated progress
		} catch (e: any) {
			console.error('Complete practice error:', e)
			setError(e?.message || 'Failed to complete practice')
		}
	}

	useEffect(() => {
		load()
	}, [])

	if (loading && practices.length === 0) {
		return (
			<div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
				<Loader2 className="h-8 w-8 animate-spin text-primary"/>
				<p className=" text-sm">Загружаем практики...</p>
			</div>
		)
	}

	return (
		<div className="flex flex-col gap-6 p-4 max-w-5xl mx-auto w-full pb-24">
			<div className="space-y-1 mt-2 flex items-center justify-between">
				<div>
					<PageHeader text="Практики" icon={Brain}/>
					<p className="leading-relaxed text-sm mt-1">
						Инструменты для работы с умом и кармой
					</p>
				</div>
				<Button variant="ghost" size="icon" onClick={load} disabled={loading}>
					<RefreshCw className={cn("h-5 w-5", loading && "animate-spin")}/>
				</Button>
			</div>

			{error && (
				<div
					className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm font-medium border border-destructive/20">
					{error}
				</div>
			)}

			<div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
				{/* Habits Section */}
				<div className="space-y-4">
					<h2 className="text-lg font-semibold flex items-center gap-2 text-white">
						<Repeat className="h-5 w-5"/>
						Мои привычки
					</h2>
					<div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
						{habits.length === 0 && (
							<div
								className="text-center py-8  bg-secondary/20 rounded-xl border border-dashed border-secondary text-sm col-span-full">
								Пока нет активных привычек
							</div>
						)}
						{habits.map((h) => (
							<Card key={h.id}
								  className="border-none shadow-sm bg-gradient-to-r from-blue-50/80 to-indigo-50/80 backdrop-blur-main border-l-4 border-l-blue-500">
								<CardContent className="p-4 flex items-center justify-between">
									<div>
										<div className="font-semibold text-foreground flex items-center gap-2">
											{h.practice_id}
											{h.is_active &&
                                                <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse"/>}
										</div>
										<div className="flex flex-wrap gap-2 mt-2 text-xs ">
                      <span className="flex items-center gap-1 bg-white/60 border border-white/20 px-2 py-1 rounded">
                        <CalendarDays className="h-3 w-3"/>
						  {h.frequency}
                      </span>
											<span
												className="flex items-center gap-1 bg-white/60 border border-white/20 px-2 py-1 rounded">
                        <Clock className="h-3 w-3"/>
												{h.preferred_time}
                      </span>
											<span
												className="flex items-center gap-1 bg-white/60 border border-white/20 px-2 py-1 rounded">
                        <Dumbbell className="h-3 w-3"/>
												{h.duration} мин
                      </span>
										</div>
									</div>
								</CardContent>
							</Card>
						))}
					</div>
				</div>

				{/* AI Recommendations Section for New Users */}
				{recommendations.length > 0 && (
					<div className="space-y-4">
						<h2 className="text-lg font-semibold flex items-center gap-2 text-white">
							<Sparkles className="h-5 w-5 text-yellow-300"/>
							AI Рекомендации для тебя
						</h2>
						<div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
							{recommendations.map((p, idx) => {
								const practiceId = p.id
								
								return (
									<Card key={`rec-${p.name}-${idx}`}
										  className="border border-yellow-500/30 bg-gradient-to-r from-yellow-50/10 to-amber-50/10 backdrop-blur-main">
										<CardHeader className="bg-yellow-500/20 border-b border-yellow-500/20 pb-3 pt-4">
											<div className="flex justify-between items-start">
												<CardTitle className="text-base font-semibold text-white">{p.name}</CardTitle>
												<div className="flex items-center gap-2">
													<div className="flex items-center gap-1 text-yellow-300 text-xs">
														<Sparkles className="h-3 w-3"/>
														AI подобрал
													</div>
													<div
														className="px-2 py-0.5 rounded-full bg-yellow-500/40 text-[10px] font-bold uppercase tracking-wider border border-yellow-500/20 text-white">
														{p.category}
													</div>
												</div>
											</div>
										</CardHeader>
										<CardContent className="p-4 pt-3">
											<div className="flex items-center gap-2 text-xs mb-3 text-white/80">
												<Clock className="h-3 w-3"/>
												<span>{p.duration} мин</span>
											</div>
											
											<div
												className="text-sm text-white/70 whitespace-pre-wrap leading-relaxed mb-4">
												{p.content}
											</div>
											
											<Button
												className="w-full shadow-lg shadow-yellow-500/20 bg-yellow-500 hover:bg-yellow-600 text-white"
												size="sm"
												onClick={() => startPractice(practiceId)}
											>
												<Plus className="h-3.5 w-3.5 mr-2"/>
												Начать практику
											</Button>
										</CardContent>
									</Card>
								)
							})}
						</div>
					</div>
				)}

				{/* Recommendations Section */}
				<div className="space-y-4">
					<h2 className="text-lg font-semibold flex items-center gap-2 text-white">
						<Flame className="h-5 w-5 "/>
						Рекомендации
					</h2>
					<div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
						{practices.length === 0 && (
							<div className="text-center py-8  text-sm col-span-full">
								Пока нет рекомендаций
							</div>
						)}
						{practices.map((p, idx) => {
							const practiceId = p.id || p.name.toLowerCase().replace(' ', '-') // Используем ID из Qdrant если есть
							const progress = progressMap[practiceId]
							
							// Отладка
							console.log(`Rendering practice "${p.name}":`, {
								practiceId,
								hasProgress: !!progress,
								progressData: progress,
								allProgressIds: Object.keys(progressMap)
							})
							
							return (
								<Card key={`${p.name}-${idx}`}
									  className={cn(
										"text-white transition-all duration-200",
										progress?.is_habit && "ring-2 ring-green-500/50"
									  )}>
									<CardHeader className="bg-white/20 border-b border-white/10 pb-3 pt-4">
										<div className="flex justify-between items-start">
											<CardTitle className="text-base font-semibold">{p.name}</CardTitle>
											<div className="flex items-center gap-2">
												{progress?.is_habit && (
													<div className="flex items-center gap-1 text-green-300 text-xs">
														<Target className="h-3 w-3"/>
														Привычка
													</div>
												)}
												<div
													className="px-2 py-0.5 rounded-full bg-primary/40 text-[10px] font-bold uppercase tracking-wider border border-primary/10 text-white">
													{p.category}
												</div>
											</div>
										</div>
									</CardHeader>
									<CardContent className="p-4 pt-3">
										{progress && (
											<div className="flex items-center justify-between mb-3 text-xs">
												<div className="flex items-center gap-3">
													<span className="flex items-center gap-1">
														<Flame className="h-3 w-3 text-orange-300"/>
														{progress.streak_days} дней
													</span>
													<span className="flex items-center gap-1">
														<TrendingUp className="h-3 w-3 text-blue-300"/>
														{progress.habit_score}%
													</span>
												</div>
												{!progress.is_habit && progress.habit_score > 0 && (
													<div className="w-16 h-1.5 bg-white/20 rounded-full overflow-hidden">
														<div 
															className="h-full bg-gradient-to-r from-blue-400 to-green-400 transition-all duration-300"
															style={{ width: `${progress.habit_score}%` }}
														/>
													</div>
												)}
											</div>
										)}
										
										<div className="flex items-center gap-2 text-xs mb-3">
											<Clock className="h-3 w-3"/>
											<span>{p.duration} мин</span>
										</div>
										
										<div
											className="text-sm text-white/70 whitespace-pre-wrap leading-relaxed mb-4">
											{p.content}
										</div>
										
										<div className="flex gap-2">
											{!progress ? (
												<Button
													className="flex-1 shadow-lg shadow-primary/10"
													size="sm"
													onClick={() => startPractice(practiceId)}
												>
													<Plus className="h-3.5 w-3.5 mr-2"/>
													Сделать привычкой
												</Button>
											) : !progress.is_habit ? (
												<>
													<Button
														className="flex-1 shadow-lg shadow-primary/10"
														size="sm"
														onClick={() => completePracticeSession(practiceId)}
													>
														<Play className="h-3.5 w-3.5 mr-2"/>
														Выполнить
													</Button>
													<Button
														variant="outline"
														size="sm"
														onClick={() => navigate(`/journal?description=${encodeURIComponent('Практика: ' + p.name)}&action_type=practice`)}
													>
														В журнал
													</Button>
												</>
											) : (
												<Button
													className="flex-1 shadow-lg shadow-green-500/10"
													size="sm"
													variant="outline"
													onClick={() => navigate(`/journal?description=${encodeURIComponent('Привычка: ' + p.name)}&action_type=practice`)}
												>
													<Target className="h-3.5 w-3.5 mr-2"/>
													Поддерживать
												</Button>
											)}
										</div>
									</CardContent>
								</Card>
							)
						})}
					</div>
				</div>
			</div>
		</div>
	)
}
