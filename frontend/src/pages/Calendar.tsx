import { Calendar as BigCalendar, momentLocalizer } from 'react-big-calendar'
import moment from 'moment'
import 'react-big-calendar/lib/css/react-big-calendar.css'
import { useCalendarData, CalendarEvent } from '../hooks/useCalendarData'

const localizer = momentLocalizer(moment)

export default function Calendar() {
  const { events, stats, loading } = useCalendarData()
  
  const eventStyleGetter = (event: CalendarEvent) => {
    const colors = {
      seed: { backgroundColor: '#4CAF50' },
      practice: { backgroundColor: '#2196F3' },
      partner_action: { backgroundColor: '#FF9800' }
    }
    return { style: colors[event.type] }
  }
  
  if (loading) {
    return <div className="page">Загрузка...</div>
  }
  
  return (
    <div className="page">
      <h1>📅 Календарь</h1>
      
      {/* Stats Bar */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(2, 1fr)',
        gap: '12px',
        margin: '16px 0'
      }}>
        <div style={{
          background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)',
          borderRadius: '8px',
          padding: '12px',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '24px' }}>🌱</div>
          <div style={{ fontWeight: 'bold', fontSize: '20px' }}>{stats.seedsCount}</div>
          <div style={{ fontSize: '12px', opacity: 0.7 }}>Семян</div>
        </div>
        
        <div style={{
          background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)',
          borderRadius: '8px',
          padding: '12px',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '24px' }}>🧘</div>
          <div style={{ fontWeight: 'bold', fontSize: '20px' }}>{stats.practicesCount}</div>
          <div style={{ fontSize: '12px', opacity: 0.7 }}>Практик</div>
        </div>
        
        <div style={{
          background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)',
          borderRadius: '8px',
          padding: '12px',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '24px' }}>👥</div>
          <div style={{ fontWeight: 'bold', fontSize: '20px' }}>{stats.partnerActionsCount}</div>
          <div style={{ fontSize: '12px', opacity: 0.7 }}>Действий</div>
        </div>
        
        <div style={{
          background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)',
          borderRadius: '8px',
          padding: '12px',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '24px' }}>🔥</div>
          <div style={{ fontWeight: 'bold', fontSize: '20px' }}>{stats.streakDays}</div>
          <div style={{ fontSize: '12px', opacity: 0.7 }}>Стрик</div>
        </div>
      </div>
      
      {/* Calendar */}
      <div style={{ height: '500px', marginTop: '16px' }}>
        <BigCalendar
          localizer={localizer}
          events={events}
          startAccessor="start"
          endAccessor="end"
          eventPropGetter={eventStyleGetter}
          views={['month', 'week', 'day']}
          defaultView="month"
        />
      </div>
      
      {/* Legend */}
      <div style={{ marginTop: '16px', display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: '16px', height: '16px', background: '#4CAF50', borderRadius: '4px' }}></div>
          <span style={{ fontSize: '14px' }}>Семена</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: '16px', height: '16px', background: '#2196F3', borderRadius: '4px' }}></div>
          <span style={{ fontSize: '14px' }}>Практики</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: '16px', height: '16px', background: '#FF9800', borderRadius: '4px' }}></div>
          <span style={{ fontSize: '14px' }}>Действия</span>
        </div>
      </div>
    </div>
  )
}
