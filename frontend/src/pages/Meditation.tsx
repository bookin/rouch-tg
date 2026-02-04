import { useEffect, useState } from 'react'
import { getSeeds } from '../api/client'
import { useNavigate } from 'react-router-dom'

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
            title: '☕️ Радость (Кофе-медитация)',
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

    if (loading) return <div className="page">Загрузка...</div>

    return (
        <div className="page" style={{
            background: 'linear-gradient(180deg, #fff3e0 0%, var(--tg-theme-bg-color, #fff) 100%)',
            minHeight: '100vh',
            display: 'flex',
            flexDirection: 'column'
        }}>
            <div style={{ flex: 1, padding: 20 }}>
                <h1 style={{ textAlign: 'center', color: '#ef6c00' }}>☕️ Кофе-медитация</h1>

                <div style={{
                    background: '#fff',
                    borderRadius: 20,
                    padding: 24,
                    boxShadow: '0 10px 30px rgba(0,0,0,0.05)',
                    marginTop: 20
                }}>
                    <div style={{ fontSize: '3rem', textAlign: 'center', marginBottom: 16 }}>
                        {steps[step].title.split(' ')[0]}
                    </div>
                    <h2 style={{ margin: '0 0 12px 0', textAlign: 'center' }}>{steps[step].title.split(' ')[1]}</h2>
                    <p style={{ lineHeight: '1.6', fontSize: '1.1rem', textAlign: 'center', opacity: 0.9 }}>
                        {steps[step].desc}
                    </p>

                    {step === 2 && (
                        <div style={{ marginTop: 24, display: 'grid', gap: 12 }}>
                            <div style={{ fontWeight: 700, fontSize: '0.9rem', opacity: 0.6, textTransform: 'uppercase' }}>Твои семена сегодня:</div>
                            {seeds.length === 0 && <div style={{ textAlign: 'center', padding: 20, opacity: 0.5 }}>Сегодня семян еще нет. Но ты можешь вспомнить любое доброе дело!</div>}
                            {seeds.map(s => (
                                <div
                                    key={s.id}
                                    onClick={() => toggleRejoice(s.id)}
                                    style={{
                                        padding: 16,
                                        borderRadius: 16,
                                        background: rejoiced.includes(s.id) ? '#fff3e0' : '#f5f5f5',
                                        border: rejoiced.includes(s.id) ? '2px solid #ff9800' : '2px solid transparent',
                                        cursor: 'pointer',
                                        transition: '0.2s',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: 12
                                    }}
                                >
                                    <div style={{ fontSize: '1.5rem' }}>{rejoiced.includes(s.id) ? '🌟' : '🌱'}</div>
                                    <div style={{ flex: 1 }}>
                                        <div style={{ fontWeight: 600 }}>{s.action_type === 'start' ? 'Начато' : 'Прекращено'}</div>
                                        <div style={{ fontSize: '0.9rem', opacity: 0.8 }}>{s.description}</div>
                                    </div>
                                    {rejoiced.includes(s.id) && <div style={{ color: '#ef6c00', fontWeight: 800 }}>РАДОСТЬ!</div>}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            <div style={{ padding: 20 }}>
                <button
                    onClick={handleNext}
                    style={{
                        width: '100%',
                        padding: 18,
                        borderRadius: 16,
                        border: 'none',
                        background: '#ef6c00',
                        color: '#fff',
                        fontWeight: 700,
                        fontSize: '1.1rem',
                        boxShadow: '0 4px 12px rgba(239, 108, 0, 0.3)',
                        cursor: 'pointer'
                    }}
                >
                    {step === steps.length - 1 ? 'Завершить' : 'Далее'}
                </button>
                <div style={{ textAlign: 'center', marginTop: 12, opacity: 0.4, fontSize: '0.8rem' }}>
                    Шаг {step + 1} из {steps.length}
                </div>
            </div>
        </div>
    )
}
