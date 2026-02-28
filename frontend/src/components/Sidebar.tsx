import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Home, Users, Sprout, Brain, Puzzle, Settings, LogOut } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from './ui/button'
import { isTelegramContext, logoutUser } from '@/api/client'

export function Sidebar() {
  const location = useLocation()
  const navigate = useNavigate()
  const showLogout = !isTelegramContext()

  const navItems = [
    { path: '/', icon: Home, label: 'Главная' },
    // { path: '/calendar', icon: CalendarIcon, label: 'Календарь' },
    { path: '/partners', icon: Users, label: 'Партнёры' },
    { path: '/journal', icon: Sprout, label: 'Журнал' },
    { path: '/practices', icon: Brain, label: 'Практики' },
    { path: '/problem', icon: Puzzle, label: 'Проблема' },
  ]

  return (
    <aside className="hidden md:flex flex-col w-64 h-screen fixed left-0 top-0 border-r border-white/15 bg-white/10 backdrop-blur-xl text-foreground z-50 shadow-sm">
      {/*<div className="p-6 flex items-center gap-3">*/}
      {/*  <div className="w-8 h-8 rounded-full bg-primary/90 flex items-center justify-center text-primary-foreground font-bold text-lg shadow-sm">*/}
      {/*    R*/}
      {/*  </div>*/}
      {/*  <span className="font-bold text-xl tracking-tight">Rouch</span>*/}
      {/*</div>*/}

      <nav className="flex-1 px-4 py-4 space-y-2">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path
          const Icon = item.icon
          return (
            <Link
              key={item.path}
              to={item.path}
            >
              <Button
                variant={isActive ? "secondary" : "ghost"}
                className={cn(
                  "w-full justify-start gap-3 h-12 text-base font-medium cursor-pointer",
                  isActive ? "bg-secondary text-secondary-foreground" : "text-white"
                )}
              >
                <Icon className={cn("h-5 w-5", isActive && "text-secondary-foreground")} />
                {item.label}
              </Button>
            </Link>
          )
        })}
      </nav>

      <div className="p-4 border-t border-border space-y-2 border-white/15">
         <Button variant="ghost" className="w-full justify-start gap-3 h-12 text-base text-white cursor-pointer">
            <Settings className="h-5 w-5" />
            Настройки
         </Button>
         {showLogout && (
           <Button
             variant="ghost"
             className="w-full justify-start gap-3 h-12 text-base text-white/60 hover:text-white cursor-pointer"
             onClick={() => { logoutUser(); navigate('/login') }}
           >
             <LogOut className="h-5 w-5" />
             Выйти
           </Button>
         )}
      </div>
    </aside>
  )
}
