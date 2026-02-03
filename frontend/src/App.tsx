import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Calendar from './pages/Calendar'
import Partners from './pages/Partners'
import SeedJournal from './pages/SeedJournal'
import Practices from './pages/Practices'
import Problem from './pages/Problem'

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

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/calendar" element={<Calendar />} />
        <Route path="/partners" element={<Partners />} />
        <Route path="/journal" element={<SeedJournal />} />
        <Route path="/practices" element={<Practices />} />
        <Route path="/problem" element={<Problem />} />
      </Routes>
      <BottomNav />
    </Router>
  )
}

export default App
