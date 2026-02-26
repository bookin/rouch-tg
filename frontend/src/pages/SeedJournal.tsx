import {FormEvent, useEffect, useState} from 'react'
import {useSearchParams} from 'react-router-dom'
import {createSeed, getSeeds, getPartners, SeedCreatePayload} from '../api/client'
import {Sprout, Heart, Users, Brain, History, Loader2, Sparkles, Leaf, HelpCircle} from 'lucide-react'
import {cn} from '@/lib/utils'
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card'
import {Button} from '@/components/ui/button'
import {Textarea} from '@/components/ui/textarea'
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from '@/components/ui/select'
import {Slider} from '@/components/ui/slider'
import {Checkbox} from '@/components/ui/checkbox'
import {Label} from '@/components/ui/label'
import {Popover, PopoverContent, PopoverPortal, PopoverTrigger} from "@radix-ui/react-popover";
import PageHeader from "@/components/ui/PageHeader.tsx";

interface SeedItem {
	id: string
	timestamp: string
	action_type: string
	description: string
	partner_group: string
	intention_score: number
	emotion_level: number
	strength_multiplier: number
	estimated_maturation_days: number
}

const ACTION_TYPES = [
	{value: 'giving', label: 'Даяние', description: '(Щедрость)'},
	{value: 'kindness', label: 'Доброта', description: '(Этика)'},
	{value: 'patience', label: 'Терпение'},
	{value: 'effort', label: 'Усердие'},
	{value: 'concentration', label: 'Концентрация'},
	{value: 'wisdom', label: 'Мудрость'}
]

const ActionTypeLabel = (type: string) => ACTION_TYPES.find(t => t.value === type)?.label || type

const PARTNER_GROUPS = [
	{value: 'source', label: 'Источник', description: '(Родители/Учителя)'},
	{value: 'ally', label: 'Соратники', description: '(Партнеры/Коллеги)'},
	{value: 'protege', label: 'Подопечные', description: '(Клиенты/Дети)'},
	{value: 'world', label: 'Внешний мир'}
]

const PartnerGroupLabel = (group: string) => PARTNER_GROUPS.find(g => g.value === group)?.label || group

export default function SeedJournal() {
	const [searchParams] = useSearchParams()
	const [loading, setLoading] = useState(true)
	const [seeds, setSeeds] = useState<SeedItem[]>([])
	const [error, setError] = useState<string | null>(null)

	const [description, setDescription] = useState(searchParams.get('description') || '')
	const [actionType, setActionType] = useState('kindness')
	const [partnerGroup, setPartnerGroup] = useState('world')
	const [intentionScore, setIntentionScore] = useState([7])
	const [emotionLevel, setEmotionLevel] = useState([7])
	const [understanding, setUnderstanding] = useState(true)
	const [submitting, setSubmitting] = useState(false)

	const load = async () => {
		try {
			setError(null)
			setLoading(true)
			const data = await getSeeds(200)
			setSeeds(data.seeds || [])

			// Handle partner_ids if present to pre-select group
			const pids = searchParams.get('partner_ids')
			if (pids) {
				const partnersData = await getPartners()
				const firstPid = pids.split(',')[0]
				const partner = partnersData.partners.find((p: any) => p.id === firstPid)
				if (partner) {
					const group = partnersData.groups.find((g: any) => g.id === partner.group_id)
					if (group && group.universal_category) {
						setPartnerGroup(group.universal_category)
					}
				}
			}
		} catch (e: any) {
			setError(e?.message || 'Failed to load seeds')
		} finally {
			setLoading(false)
		}
	}

	useEffect(() => {
		load()
	}, [])

	const onCreate = async (e: FormEvent) => {
		e.preventDefault()
		if (!description.trim()) return

		const payload: SeedCreatePayload = {
			description: description.trim(),
			action_type: actionType,
			partner_group: partnerGroup,
			intention_score: intentionScore[0],
			emotion_level: emotionLevel[0],
			understanding,
			estimated_maturation_days: 21,
			strength_multiplier: 1.5
		}

		try {
			setSubmitting(true)
			setError(null)
			await createSeed(payload)
			setDescription('')
			setIntentionScore([7])
			setEmotionLevel([7])
			setUnderstanding(true)
			await load()
		} catch (err: any) {
			setError(err?.message || 'Failed to create seed')
		} finally {
			setSubmitting(false)
		}
	}

	if (loading && seeds.length === 0) {
		return (
			<div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
				<Loader2 className="h-8 w-8 animate-spin text-primary"/>
				<p className=" text-sm">Открываем журнал...</p>
			</div>
		)
	}

	return (
		<div className="flex flex-col gap-6 p-4 max-w-5xl mx-auto w-full pb-24">
			<div className="space-y-1 mt-2">
				<PageHeader text="Журнал семян" icon={Sprout} />
				<p className="leading-relaxed">
					Записывай свои добрые дела, чтобы они проросли в большие результаты.
				</p>
			</div>

			{error && (
				<div
					className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm font-medium border border-destructive/20">
					{error}
				</div>
			)}

			<div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
				{/* Create Seed Form - Left Column */}
				<div className="lg:col-span-5 xl:col-span-4">
					<Card className="border-primary/20 shadow-md sticky top-6">
						<CardHeader className="pb-3 pt-3 bg-secondary/30">
							<CardTitle className="flex items-center gap-2 text-lg text-white">
								<Leaf className="h-5 w-5"/>
								Посадить семя
							</CardTitle>
						</CardHeader>
						<CardContent className="pt-5 space-y-5">
							<form onSubmit={onCreate} className="space-y-5">
								<div className="space-y-2">
									<Label>Что ты сделал(а)?</Label>
									<Textarea
										value={description}
										onChange={(e) => setDescription(e.target.value)}
										placeholder="Я помог коллеге разобраться с..."
										className="min-h-[100px] "
									/>
								</div>

								<div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-1">
									<div className="space-y-2">
										<Label>Тип действия</Label>
										<Select  value={actionType} onValueChange={setActionType}>
											<SelectTrigger className="">
												<SelectValue/>
											</SelectTrigger>
											<SelectContent className="bg-white backdrop-blur-md text-primary">
												{ACTION_TYPES.map(t => (
													<SelectItem
														key={t.value}
														value={t.value}
														description={<div className="text-[0.6rem]">{t.description}</div>}
													>
														{t.label}
													</SelectItem>
												))}
											</SelectContent>
										</Select>
									</div>

									<div className="space-y-2">
										<Label>Кому?</Label>
										<Select value={partnerGroup} onValueChange={setPartnerGroup}>
											<SelectTrigger className="">
												<SelectValue/>
											</SelectTrigger>
											<SelectContent className="bg-white backdrop-blur-md">
												{PARTNER_GROUPS.map(g => (
													<SelectItem
														key={g.value}
														value={g.value}
														description={<div className="text-[0.6rem]">{g.description}</div>}
													>
														{g.label}
													</SelectItem>
												))}
											</SelectContent>
										</Select>
									</div>
								</div>

								<div className="space-y-6 pt-2">
									<div className="space-y-3">
										<div className="flex justify-between">
											<Label>Сила намерения</Label>
											<span className="text-xs font-medium ">{intentionScore[0]}/10</span>
										</div>
										<Slider
											value={intentionScore}
											onValueChange={setIntentionScore}
											min={1}
											max={10}
											step={1}
											rangeClassName="bg-blue-500"
										/>
										<p className="text-xs text-muted-foreground">
											Насколько искренне ты хочешь помочь? 1-3 = просто так, 7-8 = реально хочу,
											9-10 = всем сердцем
										</p>
									</div>

									<div className="space-y-3">
										<div className="flex justify-between">
											<Label>Сила эмоции</Label>
											<span className="text-xs font-medium ">{emotionLevel[0]}/10</span>
										</div>
										<Slider
											value={emotionLevel}
											onValueChange={setEmotionLevel}
											min={1}
											max={10}
											step={1}
											rangeClassName="bg-rose-500"
										/>
										<p className="text-xs text-muted-foreground">
											Насколько сильно ты почувствовал момент? 1-3 = спокойно, 7-8 = тронут, 9-10
											= до слёз
										</p>
									</div>
								</div>

								<div className="flex items-center space-x-2 pt-2">
									<Checkbox
										id="understanding"
										checked={understanding}
										onCheckedChange={(c) => setUnderstanding(c as boolean)}
										className="h-5 w-5"
									/>
									<div className="flex items-center gap-1">
										<Label
											htmlFor="understanding"
											className="text-sm font-normal cursor-pointer"
										>
											Я понимаю, как это работает
										</Label>
										<Popover>
											<PopoverTrigger asChild>
												<HelpCircle
													className="h-4 w-4 text-muted-foreground cursor-help hover:text-foreground transition-colors"/>
											</PopoverTrigger>
											<PopoverPortal>
												<PopoverContent className="w-80" align="center">
													<Card className="backdrop-blur-sm">
														<CardContent className="p-3">
															<div className="space-y-2 text-xs">
																<p>
																	Это когда ты действуешь осознанно, понимая суть
																	процесса.
																	Такое отношение усиливает результат в несколько раз,
																	превращая действие в посадку семени.
																</p>
																<p className="mt-2">
																	Без понимания - просто поступок.
																	С понимание - сеешь будущее, которое обязательно
																	прорастёт.
																</p>
															</div>
														</CardContent>
													</Card>
												</PopoverContent>
											</PopoverPortal>
										</Popover>
									</div>
								</div>

								<Button
									type="submit"
									className="w-full bg-primary hover:bg-primary/90"
									disabled={!description.trim() || submitting}
								>
									{submitting ? (
										<>
											<Loader2 className="mr-2 h-4 w-4 animate-spin"/>
											Сажаем...
										</>
									) : (
										<>
											Посадить семя
											<Sparkles className="ml-2 h-4 w-4"/>
										</>
									)}
								</Button>
							</form>
						</CardContent>
					</Card>
				</div>

				{/* History - Right Column */}
				<div className="lg:col-span-7 xl:col-span-8 space-y-4">
					<h2 className="text-lg font-semibold flex items-center gap-2">
						<History className="h-5 w-5 "/>
						История посевов
					</h2>

					<div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
						{seeds.length === 0 && (
							<div
								className="text-center py-10  bg-secondary/20 rounded-xl border border-dashed col-span-full">
								Пока нет записей. Посади свое первое семя!
							</div>
						)}

						{seeds.map((s) => (
							<Card key={s.id} className="overflow-hidden">
								<div className={cn(
									"h-1 w-full",
									s.action_type === 'kindness' ? "bg-rose-400" :
									s.action_type === 'giving' ? "bg-blue-400" :
									"bg-green-400"
								)}/>
								<CardContent className="p-4 flex flex-col h-full">
									<div className="flex items-start gap-4 flex-1">
										<p className="font-medium leading-snug">{s.description}</p>
									</div>

									<div className="flex flex-wrap gap-2 text-xs mt-2 items-end justify-between">
										<div className="flex flex-wrap gap-2 text-xs flex-col items-start">
											<div
												className="flex items-center gap-1 bg-white/10 border border-white/20 px-2 py-1 rounded-md">
												<Heart className="h-3 w-3"/>
												{ActionTypeLabel(s.action_type)}
											</div>
											<div
												className="flex items-center gap-1 bg-white/10 border border-white/20 px-2 py-1 rounded-md">
												<Users className="h-3 w-3"/>
												{PartnerGroupLabel(s.partner_group)}
											</div>
										</div>
										<div className="flex flex-wrap gap-2 text-xs flex-col items-end justify-between">
											<div
												className="flex items-center gap-1 bg-white/10 border border-white/20 px-2 py-1 rounded-md ml-auto">
												<Brain className="h-3 w-3"/>
												{s.strength_multiplier}x
											</div>
											<div>
												<span className="text-[10px] text-muted-foreground whitespace-nowrap">
													{new Date(s.timestamp).toLocaleDateString()}
												</span>
											</div>
										</div>
									</div>
								</CardContent>
							</Card>
						))}
					</div>
				</div>
			</div>
		</div>
	)
}
