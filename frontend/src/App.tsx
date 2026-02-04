import { BrowserRouter as Router, Routes, Route, Link, useLocation, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { getUser } from './api/client'
import { useTelegram } from './hooks/useTelegram'
import Dashboard from './pages/Dashboard'
import Calendar from './pages/Calendar'
import Partners from './pages/Partners'
import SeedJournal from './pages/SeedJournal'
import Practices from './pages/Practices'
import Problem from './pages/Problem'
import Meditation from './pages/Meditation'
import Onboarding from './pages/Onboarding'

function BottomNav() {
  const location = useLocation()

  return (
    <nav className="bottom-nav">
      <Link to="/" className={`nav-item ${location.pathname === '/' ? 'active' : ''}`}>
        <span className="nav-icon">🏠</span>
        <span>Главная</span>
      </Link>
      <Link to="/calendar" className={`nav-item ${location.pathname === '/calendar' ? 'active' : ''}`}>
        <span className="nav-icon">📅</span>
        <span>Календарь</span>
      </Link>
      <Link to="/partners" className={`nav-item ${location.pathname === '/partners' ? 'active' : ''}`}>
        <span className="nav-icon">👥</span>
        <span>Партнёры</span>
      </Link>
      <Link to="/journal" className={`nav-item ${location.pathname === '/journal' ? 'active' : ''}`}>
        <span className="nav-icon">🌱</span>
        <span>Журнал</span>
      </Link>
      <Link to="/practices" className={`nav-item ${location.pathname === '/practices' ? 'active' : ''}`}>
        <span className="nav-icon">🧘</span>
        <span>Практики</span>
      </Link>
      <Link to="/problem" className={`nav-item ${location.pathname === '/problem' ? 'active' : ''}`}>
        <span className="nav-icon">🧩</span>
        <span>Проблема</span>
      </Link>
    </nav>
  )
}

function AppContent() {
  const { isReady } = useTelegram()
  const navigate = useNavigate()
  const location = useLocation()
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    // Only check when Telegram WebApp is ready (or in dev mode)
    if (!isReady) return

    const checkUser = async () => {
      try {
        const user = await getUser()
        // If user hasn't completed onboarding and isn't already there
        if (!user.last_onboarding_update && location.pathname !== '/onboarding') {
          navigate('/onboarding')
        }
      } catch (error) {
        console.error('Failed to check user status:', error)
      } finally {
        setChecking(false)
      }
    }

    checkUser()
  }, [isReady, navigate, location.pathname])

  if (checking) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        background: 'var(--tg-theme-bg-color, #fff)'
      }}>
        <div style={{ fontSize: '24px' }}>🧘</div>
      </div>
    )
  }

  return (
    <>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/calendar" element={<Calendar />} />
        <Route path="/partners" element={<Partners />} />
        <Route path="/journal" element={<SeedJournal />} />
        <Route path="/practices" element={<Practices />} />
        <Route path="/problem" element={<Problem />} />
        <Route path="/meditation" element={<Meditation />} />
        <Route path="/onboarding" element={<Onboarding />} />
      </Routes>
      <ConditionalBottomNav />
    </>
  )
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  )
}

function ConditionalBottomNav() {
  const location = useLocation()
  // Hide nav on onboarding page
  if (location.pathname === '/onboarding') return null
  return <BottomNav />
}

export default App
