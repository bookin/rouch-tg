import { BrowserRouter as Router, Routes, Route, useLocation, useNavigate, Navigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { getUser, isTelegramContext, isAuthenticated } from './api/client'
import { useTelegram } from './hooks/useTelegram'
import Dashboard from './pages/Dashboard'
// import Calendar from './pages/Calendar'
import Partners from './pages/Partners'
import SeedJournal from './pages/SeedJournal'
import Practices from './pages/Practices'
import Problem from './pages/Problem'
import CoffeePage from './pages/Coffee'
import Onboarding from './pages/Onboarding'
import Login from './pages/Login'
import Register from './pages/Register'
import VerifyEmail from './pages/VerifyEmail'
import Settings from './pages/Settings'
import MergeAccounts from './pages/MergeAccounts'
import Layout from './components/Layout'
import Lotus from "@/components/Lotus.tsx";

function AppContent() {
  const { isReady } = useTelegram()
  const navigate = useNavigate()
  const location = useLocation()
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    const inTelegram = isTelegramContext()

    // In Telegram context, wait for WebApp to be ready
    if (inTelegram && !isReady) return

    // Skip auth check for public pages
    const publicPaths = ['/login', '/register', '/verify-email', '/merge']
    if (publicPaths.some(p => location.pathname.startsWith(p))) {
      setChecking(false)
      return
    }

    // In web context, check if we have a token
    if (!inTelegram && !isAuthenticated()) {
      setChecking(false)
			const next = `${location.pathname}${location.search}`
			sessionStorage.setItem('auth_next', next)
			localStorage.setItem('auth_next', next)
			navigate(`/login?next=${encodeURIComponent(next)}`)
      return
    }

    const checkUser = async () => {
      try {
        const user = await getUser()
        // If user hasn't completed onboarding and isn't already there
        if (!user.last_onboarding_update && location.pathname !== '/onboarding') {
          navigate('/onboarding')
        }
      } catch (error) {
        console.error('Failed to check user status:', error)
        // In web context, redirect to login on auth failure
        if (!inTelegram) {
				const next = `${location.pathname}${location.search}`
				sessionStorage.setItem('auth_next', next)
				localStorage.setItem('auth_next', next)
				navigate(`/login?next=${encodeURIComponent(next)}`)
        }
      } finally {
        setChecking(false)
      }
    }

    checkUser()
  }, [isReady, navigate, location.pathname, location.search])

  if (checking) {
    return (
      <div className="flex items-center justify-center min-h-screen text-foreground">
        <div className="animate-pulse text-4xl">🧘</div>
      </div>
    )
  }

  return (
	  <div className="mesh mesh--green">

		<Lotus/>
		  <Layout>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/" element={<Dashboard />} />
        {/*<Route path="/calendar" element={<Calendar />} />*/}
        <Route path="/partners" element={<Partners />} />
        <Route path="/journal" element={<SeedJournal />} />
        <Route path="/practices" element={<Practices />} />
        <Route path="/problem" element={<Problem />} />
        <Route path="/cofee" element={<Navigate to="/coffee" replace />} />
        <Route path="/coffee" element={<CoffeePage />} />
        <Route path="/meditation" element={<Navigate to="/coffee" replace />} />
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/verify-email" element={<VerifyEmail />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/merge" element={<MergeAccounts />} />
      </Routes>
    </Layout>
	  </div>

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
