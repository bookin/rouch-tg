import { Link, useLocation } from 'react-router-dom'
import { Home, Calendar as CalendarIcon, Users, Sprout, Brain, Puzzle } from 'lucide-react'
import { cn } from '@/lib/utils'

export function BottomNav() {
  const location = useLocation()

  const navItems = [
    { path: '/', icon: Home, label: 'Главная' },
    { path: '/calendar', icon: CalendarIcon, label: 'Календарь' },
    { path: '/partners', icon: Users, label: 'Партнёры' },
    { path: '/journal', icon: Sprout, label: 'Журнал' },
    { path: '/practices', icon: Brain, label: 'Практики' },
    { path: '/problem', icon: Puzzle, label: 'Проблема' },
  ]

  return (
    <nav className="z-50 fixed bottom-0 left-0 right-0 z-50 bg-white/10 backdrop-blur-xl border-t border-white/20 pb-[env(safe-area-inset-bottom)] md:hidden shadow-[0_-5px_20px_-5px_rgba(0,0,0,0.05)]">
      <div className="flex justify-around items-center h-16 px-2">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path
          const Icon = item.icon
          return (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                "flex flex-col items-center justify-center w-full h-full gap-1 text-[10px] font-medium transition-colors duration-200",
                isActive 
                  ? "text-white"
                  : " hover:text-foreground"
              )}
            >
              <Icon className={cn("h-6 w-6", isActive && "stroke-[2.5px]")} />
              <span>{item.label}</span>
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
