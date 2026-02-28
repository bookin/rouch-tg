import {ReactNode} from 'react'
import {useLocation} from 'react-router-dom'
import {Sidebar} from './Sidebar'
import {BottomNav} from './BottomNav'

interface LayoutProps {
	children: ReactNode
}

export default function Layout({children}: LayoutProps) {
	const location = useLocation()
	const isPlainPage =
		location.pathname === '/onboarding' ||
		location.pathname === '/meditation' ||
		location.pathname === '/coffee'


	if (isPlainPage) {
		return <main className="min-h-screen relative z-10">{children}</main>
	}

	return (
		<div className="relative z-10 min-h-screen text-foreground font-sans antialiased">
			{/* Desktop Sidebar */}
			<Sidebar/>

			{/* Main Content Area */}
			<div className="md:pl-64 min-h-screen flex flex-col transition-all duration-300">
				<main className="flex-1 w-full max-w-7xl mx-auto p-4 md:p-8 pb-24 md:pb-8">
					{children}
				</main>
			</div>

			{/* Mobile Bottom Navigation */}
			<BottomNav/>
		</div>
	)
}
