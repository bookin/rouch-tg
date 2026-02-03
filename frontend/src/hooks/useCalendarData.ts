import { useState, useEffect } from 'react'
import { getCalendarData, getCalendarStats } from '../api/client'

export interface CalendarEvent {
  id: string
  title: string
  start: Date
  end: Date
  type: 'seed' | 'practice' | 'partner_action'
  data: any
}

export interface CalendarStats {
  seedsCount: number
  practicesCount: number
  partnerActionsCount: number
  streakDays: number
}

export const useCalendarData = (startDate?: Date, endDate?: Date) => {
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [stats, setStats] = useState<CalendarStats>({
    seedsCount: 0,
    practicesCount: 0,
    partnerActionsCount: 0,
    streakDays: 0
  })
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        
        const start = startDate || new Date(new Date().setDate(1))
        const end = endDate || new Date()
        
        const [data, statsData] = await Promise.all([
          getCalendarData(start, end),
          getCalendarStats(start, end)
        ])
        
        // Transform data to calendar events
        const calendarEvents: CalendarEvent[] = [
          ...data.seeds.map((s: any) => ({
            id: s.id,
            title: `🌱 ${s.action_type}: ${s.description}`,
            start: new Date(s.timestamp),
            end: new Date(s.timestamp),
            type: 'seed' as const,
            data: s
          })),
          ...data.practices.map((p: any) => ({
            id: p.id,
            title: `🧘 ${p.name}`,
            start: new Date(p.timestamp),
            end: new Date(p.timestamp),
            type: 'practice' as const,
            data: p
          })),
          ...data.partnerActions.map((a: any) => ({
            id: a.id,
            title: `👥 ${a.partner_name}: ${a.action}`,
            start: new Date(a.timestamp),
            end: new Date(a.timestamp),
            type: 'partner_action' as const,
            data: a
          }))
        ]
        
        setEvents(calendarEvents)
        setStats(statsData)
      } catch (error) {
        console.error('Error loading calendar data:', error)
      } finally {
        setLoading(false)
      }
    }
    
    fetchData()
  }, [startDate, endDate])
  
  return { events, stats, loading }
}
