import {Calendar as BigCalendar, momentLocalizer} from 'react-big-calendar'
import moment from 'moment'
import 'react-big-calendar/lib/css/react-big-calendar.css'
import {useCalendarData, CalendarEvent} from '../hooks/useCalendarData'
import {Card, CardContent} from '@/components/ui/card'
import {Loader2, Calendar as CalendarIcon, Sprout, Brain, Users, Flame} from 'lucide-react'
import PageHeader from "@/components/ui/PageHeader.tsx";

const localizer = momentLocalizer(moment)

export default function Calendar() {
	const {events, stats, loading} = useCalendarData()

	const eventStyleGetter = (event: CalendarEvent) => {
		let backgroundColor = '#3390ec'
		if (event.type === 'seed') backgroundColor = '#10b981' // Green-500
		if (event.type === 'practice') backgroundColor = '#3b82f6' // Blue-500
		if (event.type === 'partner_action') backgroundColor = '#f59e0b' // Amber-500

		return {
			style: {
				backgroundColor,
				borderRadius: '4px',
				// opacity: 0.8,
				color: 'white',
				border: 'none',
				display: 'block',
				fontSize: '0.75rem'
			}
		}
	}

	if (loading) {
		return (
			<div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
				<Loader2 className="h-8 w-8 animate-spin text-primary"/>
				<p className=" text-sm">Загружаем календарь...</p>
			</div>
		)
	}

	return (
		<div className="flex flex-col gap-6 p-4 max-w-5xl mx-auto w-full pb-24">
			<div className="space-y-1 mt-2">
				<PageHeader text="Календарь" icon={CalendarIcon}/>
				<p className="leading-relaxed text-sm mt-1">
					Твоя история кармических посевов и практик
				</p>
			</div>

			{/* Stats Bar */}
			<div className="grid grid-cols-2 md:grid-cols-4 gap-3">
				<Card>
					<CardContent className="p-4 flex flex-col items-center justify-center text-center">
						<Sprout className="h-6 w-6 text-green-600 mb-2"/>
						<div className="text-2xl font-bold">{stats.seedsCount}</div>
						<div className="text-xs uppercase tracking-wider font-semibold">Семян</div>
					</CardContent>
				</Card>

				<Card>
					<CardContent className="p-4 flex flex-col items-center justify-center text-center">
						<Brain className="h-6 w-6 text-blue-600 mb-2"/>
						<div className="text-2xl font-bold">{stats.practicesCount}</div>
						<div className="text-xs uppercase tracking-wider font-semibold">Практик</div>
					</CardContent>
				</Card>


				{stats.partnerActionsCount > 0 && (
					<Card>
						<CardContent className="p-4 flex flex-col items-center justify-center text-center">
							<Users className="h-6 w-6 text-amber-600 mb-2"/>
							<div className="text-2xl font-bold ">{stats.partnerActionsCount}</div>
							<div className="text-xs  uppercase tracking-wider font-semibold">Действий</div>
						</CardContent>
					</Card>
				)}

				<Card>
					<CardContent className="p-4 flex flex-col items-center justify-center text-center">
						<Flame className="h-6 w-6 text-rose-600 mb-2"/>
						<div className="text-2xl font-bold ">{stats.streakDays}</div>
						<div className="text-xs  uppercase tracking-wider font-semibold">Дней подряд</div>
					</CardContent>
				</Card>
			</div>

			{/* Calendar */}
			<Card>
				<CardContent className="p-0">
					<div className="h-[450px] md:h-[600px] bg-transparent p-2 text-xs md:text-sm">
						<BigCalendar
							localizer={localizer}
							events={events}
							startAccessor="start"
							endAccessor="end"
							eventPropGetter={eventStyleGetter}
							views={['month', 'week', 'day']}
							defaultView="month"
							toolbar={true}
							className="font-sans bg-transparent"
						/>
					</div>
				</CardContent>
			</Card>

			{/* Legend */}
			<div
				className="flex flex-wrap gap-4 justify-center bg-white/10 backdrop-blur-md border border-white/20 p-3 rounded-xl shadow-sm">
				<div className="flex items-center gap-2">
					<div className="w-3 h-3 bg-green-500 rounded-full shadow-sm"></div>
					<span className="text-xs font-medium text-foreground/80">Семена</span>
				</div>
				<div className="flex items-center gap-2">
					<div className="w-3 h-3 bg-blue-500 rounded-full shadow-sm"></div>
					<span className="text-xs font-medium text-foreground/80">Практики</span>
				</div>
				{stats.partnerActionsCount > 0 && (
					<div className="flex items-center gap-2">
						<div className="w-3 h-3 bg-amber-500 rounded-full shadow-sm"></div>
						<span className="text-xs font-medium text-foreground/80">Действия</span>
					</div>
				)}
			</div>
		</div>
	)
}
