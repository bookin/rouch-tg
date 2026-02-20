import { BrowserRouter as Router, Routes, Route, useLocation, useNavigate } from 'react-router-dom'
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
import Layout from './components/Layout'

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
      <div className="flex items-center justify-center min-h-screen bg-background text-foreground">
        <div className="animate-pulse text-4xl">🧘</div>
      </div>
    )
  }

  return (
    <Layout>
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
    </Layout>
  )
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  )
}

export default App
