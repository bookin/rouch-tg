import { useEffect, useState } from 'react'
import { getSeeds } from '../api/client'
import { useNavigate } from 'react-router-dom'
import { Coffee, Sprout, Sparkles, ChevronRight, Star } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'

export default function Meditation() {
    const navigate = useNavigate()
    const [seeds, setSeeds] = useState<any[]>([])
    const [loading, setLoading] = useState(true)
    const [step, setStep] = useState(0)
    const [rejoiced, setRejoiced] = useState<string[]>([])

    useEffect(() => {
        const fetchTodaySeeds = async () => {
            try {
                const data = await getSeeds()
                // Filter for today
                const today = new Date().toISOString().split('T')[0]
                const todaySeeds = (data || []).filter((s: any) => s.timestamp.startsWith(today))
                setSeeds(todaySeeds)
            } catch (e) {
                console.error('Failed to fetch seeds', e)
            } finally {
                setLoading(false)
            }
        }
        fetchTodaySeeds()
    }, [])

    const steps = [
        {
            title: '🧘 Подготовка',
            desc: 'Найди удобное место, расслабься. Сделай несколько глубоких вдохов. Представь, что твой день прошел не зря.'
        },
        {
            title: '🌱 Сегодняшние семена',
            desc: 'Вспомни все добрые дела, которые ты сделал сегодня. Каждое из них — это семя будущего успеха.'
        },
        {
            title: '☕️ Радость',
            desc: 'Порадуйся за каждое действие. Радость — это полив, без которого семена не взойдут.'
        },
        {
            title: '✨ Посвящение',
            desc: 'Направь энергию этих семян на достижение своей цели и на благо всех людей вокруг.'
        }
    ]

    const handleNext = () => {
        if (step < steps.length - 1) {
            setStep(step + 1)
        } else {
            navigate('/')
        }
    }

    const toggleRejoice = (id: string) => {
        setRejoiced(prev =>
            prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
        )
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-orange-50">
                <div className="animate-spin text-orange-500">
                    <Coffee className="h-8 w-8" />
                </div>
            </div>
        )
    }

    const progress = ((step + 1) / steps.length) * 100

    return (
        <div className="min-h-screen bg-gradient-to-b from-orange-100/60 to-background flex flex-col p-4 pb-8">
            <div className="flex-1 flex flex-col justify-center max-w-md mx-auto w-full gap-6">
                
                {/* Header */}
                <div className="text-center space-y-2 mb-4 animate-in fade-in slide-in-from-top-4 duration-700">
                    <div className="inline-flex p-3 rounded-full bg-white/50 text-orange-600 mb-2 shadow-sm backdrop-blur-main border border-white/40">
                        <Coffee className="h-8 w-8" />
                    </div>
                    <h1 className="text-2xl font-bold text-orange-900">Кофе-медитация</h1>
                    <Progress value={progress} className="h-1.5 w-full max-w-[120px] mx-auto bg-orange-100" />
                </div>

                {/* Main Card */}
                <Card className="border-white/40 shadow-soft bg-white/70 backdrop-blur-xl overflow-hidden relative">
                    <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-orange-300 to-amber-300" />
                    <CardContent className="p-8 text-center space-y-6 pt-10">
                        <div className="text-5xl animate-bounce duration-1000 filter drop-shadow-md">
                            {steps[step].title.split(' ')[0]}
                        </div>
                        
                        <div className="space-y-3">
                            <h2 className="text-2xl font-bold text-foreground">
                                {steps[step].title.split(' ').slice(1).join(' ')}
                            </h2>
                            <p className=" text-lg leading-relaxed">
                                {steps[step].desc}
                            </p>
                        </div>

                        {step === 2 && (
                            <div className="text-left space-y-3 pt-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
                                <div className="text-xs font-bold uppercase tracking-wider  text-center mb-2">
                                    Твои семена сегодня
                                </div>
                                
                                {seeds.length === 0 && (
                                    <div className="text-center p-4  italic bg-white/40 rounded-lg border border-white/30 backdrop-blur-main">
                                        Сегодня семян еще нет. Но ты можешь вспомнить любое доброе дело!
                                    </div>
                                )}

                                <div className="space-y-3 max-h-[300px] overflow-y-auto pr-1 scrollbar-none">
                                    {seeds.map(s => {
                                        const isRejoiced = rejoiced.includes(s.id)
                                        return (
                                            <div
                                                key={s.id}
                                                onClick={() => toggleRejoice(s.id)}
                                                className={cn(
                                                    "p-4 rounded-xl border transition-all cursor-pointer flex items-center gap-3 relative overflow-hidden group backdrop-blur-main",
                                                    isRejoiced 
                                                        ? "bg-orange-50/80 border-orange-200 shadow-sm" 
                                                        : "bg-white/40 hover:bg-white/60 border-white/30 hover:border-white/50"
                                                )}
                                            >
                                                <div className={cn(
                                                    "h-10 w-10 rounded-full flex items-center justify-center shrink-0 transition-colors",
                                                    isRejoiced ? "bg-orange-100 text-orange-600" : "bg-white/60 "
                                                )}>
                                                    {isRejoiced ? <Star className="h-5 w-5 fill-current" /> : <Sprout className="h-5 w-5" />}
                                                </div>
                                                
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-2 mb-0.5">
                                                        <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-white/50 text-foreground/80 border">
                                                            {s.action_type === 'start' ? 'Начато' : 'Действие'}
                                                        </span>
                                                        {isRejoiced && (
                                                            <span className="text-xs font-bold text-orange-600 animate-in fade-in zoom-in">
                                                                РАДОСТЬ!
                                                            </span>
                                                        )}
                                                    </div>
                                                    <p className="text-sm font-medium text-foreground truncate">
                                                        {s.description}
                                                    </p>
                                                </div>

                                                {isRejoiced && (
                                                    <div className="absolute right-0 top-0 bottom-0 w-1 bg-orange-400" />
                                                )}
                                            </div>
                                        )
                                    })}
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* Navigation */}
            <div className="max-w-md mx-auto w-full pt-6">
                <Button 
                    onClick={handleNext}
                    className="w-full h-14 text-lg font-bold shadow-lg shadow-orange-200 bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 border-0"
                >
                    {step === steps.length - 1 ? (
                        <>
                            Завершить
                            <Sparkles className="ml-2 h-5 w-5" />
                        </>
                    ) : (
                        <>
                            Далее
                            <ChevronRight className="ml-2 h-5 w-5" />
                        </>
                    )}
                </Button>
                <div className="text-center mt-4 text-xs  font-medium uppercase tracking-widest">
                    Шаг {step + 1} из {steps.length}
                </div>
            </div>
        </div>
    )
}
