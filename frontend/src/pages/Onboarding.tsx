import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, logoutUser } from '../api/client'
import { Loader2, ArrowRight, ArrowLeft, LogOut, Sparkles } from 'lucide-react'
import {Button, ButtonOption} from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'

interface OnboardingOption {
    id: string
    label: string
}

interface OnboardingStep {
    step: string
    step_number: number
    total_steps: number
    message: string
    input_type: string
    options: OnboardingOption[]
    field: string | null
    completed: boolean
    prev_step?: string | null
    current_value?: any
}

export default function Onboarding() {
    const navigate = useNavigate()
    const [currentStep, setCurrentStep] = useState<OnboardingStep | null>(null)
    const [loading, setLoading] = useState(true)
    const [submitting, setSubmitting] = useState(false)
    
    // Form state
    const [singleChoice, setSingleChoice] = useState<string>('')
    const [multiChoice, setMultiChoice] = useState<string[]>([])
    const [textInput, setTextInput] = useState('')

    useEffect(() => {
        startOnboarding()
    }, [])

    const startOnboarding = async () => {
        try {
            setLoading(true)
            const response = await api.get('/api/onboarding/start')
            const step = response.data as OnboardingStep

            if (step.completed) {
                navigate('/')
                return
            }

            setupStep(step)
            setLoading(false)
        } catch (error) {
            console.error('Failed to start onboarding:', error)
            setLoading(false)
        }
    }

    const loadStep = async (stepId: string) => {
        try {
            setLoading(true)
            const response = await api.get(`/api/onboarding/step/${stepId}`)
            setupStep(response.data as OnboardingStep)
            setLoading(false)
        } catch (error) {
            console.error('Failed to load step:', error)
            setLoading(false)
        }
    }

    const setupStep = (step: OnboardingStep) => {
        setCurrentStep(step)
        
        // Reset local state based on current value or defaults
        setSingleChoice('')
        setMultiChoice([])
        setTextInput('')
        
        if (step.current_value !== undefined && step.current_value !== null) {
            const hasOption = (val: string) => step.options.some(opt => opt.id === val)
            
            if (step.input_type === 'single_choice') {
                const val = String(step.current_value)
                if (hasOption(val)) {
                    setSingleChoice(val)
                } else if (val) {
                    setSingleChoice('other')
                    setTextInput(val)
                }
            } else if (step.input_type === 'multi_choice') {
                const vals = Array.isArray(step.current_value) ? step.current_value : []
                const standardVals = vals.filter(v => hasOption(String(v)))
                const customVals = vals.filter(v => !hasOption(String(v)) && String(v) !== 'none')
                
                let finalMulti = [...standardVals]
                if (customVals.length > 0) {
                    finalMulti.push('other')
                    setTextInput(customVals[0])
                }
                
                setMultiChoice(finalMulti)
            } else if (step.input_type === 'text_optional') {
                if (step.current_value && step.current_value !== 'skip') {
                    setTextInput(String(step.current_value))
                }
            }
        }
    }

    const handleLogout = () => {
        logoutUser()
        navigate('/login')
    }

    const handleBack = () => {
        if (currentStep?.prev_step) {
            loadStep(currentStep.prev_step)
        }
    }

    const submitAnswer = async (answer?: string, answers?: string[]) => {
        if (!currentStep) return

        try {
            setSubmitting(true)
            const response = await api.post('/api/onboarding/answer', {
                step: currentStep.step,
                answer,
                answers
            })

            const nextStep = response.data as OnboardingStep

            if (nextStep.completed) {
                setCurrentStep(nextStep)
                setTimeout(() => {
                    navigate('/')
                }, 2000)
            } else {
                setupStep(nextStep)
            }
        } catch (error) {
            console.error('Failed to submit answer:', error)
        } finally {
            setSubmitting(false)
        }
    }

    const handleNext = () => {
        if (!currentStep) return

        if (currentStep.input_type === 'single_choice' || currentStep.input_type === 'confirm') {
            let val = singleChoice || (currentStep.options.length > 0 ? currentStep.options[0].id : 'continue')
            if (val === 'other' && textInput.trim()) {
                val = textInput.trim()
            }
            submitAnswer(val)
        } else if (currentStep.input_type === 'multi_choice') {
            let finalAnswers = [...multiChoice]
            if (finalAnswers.includes('other') && textInput.trim()) {
                finalAnswers = finalAnswers.filter(a => a !== 'other')
                finalAnswers.push(textInput.trim())
            }
            submitAnswer(undefined, finalAnswers)
        } else if (currentStep.input_type === 'text_optional') {
            const val = textInput.trim() || 'skip'
            submitAnswer(val)
        }
    }

    const isNextDisabled = () => {
        if (!currentStep || submitting) return true
        if (currentStep.input_type === 'single_choice') {
            if (!singleChoice) return true
            if (singleChoice === 'other' && !textInput.trim()) return true
        }
        if (currentStep.input_type === 'multi_choice') {
            if (multiChoice.length === 0) return true
            if (multiChoice.includes('other') && !textInput.trim()) return true
        }
        return false
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        )
    }

    if (!currentStep) return null

    const progressPercent = Math.round((currentStep.step_number / currentStep.total_steps) * 100)

    if (currentStep.completed) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen p-4">
                <Card className="max-w-md w-full bg-white/10 border-white/20 backdrop-blur-md shadow-xl text-center p-8">
                    <Sparkles className="w-16 h-16 text-yellow-300 mx-auto mb-6" />
                    <h2 className="text-2xl font-bold text-white mb-4 whitespace-pre-wrap">
                        {currentStep.message}
                    </h2>
                    <Loader2 className="h-6 w-6 animate-spin text-white/50 mx-auto mt-8" />
                </Card>
            </div>
        )
    }

    return (
        <div className="flex flex-col min-h-screen max-w-2xl mx-auto p-4 md:p-6 w-full relative z-10">
            {/* Header */}
            <div className="flex justify-between items-center mb-8 mt-4">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white shadow-md">
                        <Sparkles className="h-5 w-5" />
                    </div>
                    <div>
                        <h1 className="text-lg font-bold text-white leading-tight">Rouch</h1>
                        <p className="text-xs text-white/60 font-medium">Кармический менеджер</p>
                    </div>
                </div>
                <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={handleLogout} 
                    className="text-white/80 hover:text-white hover:bg-white/10"
                >
                    <LogOut className="h-4 w-4 mr-2" />
                    Выйти
                </Button>
            </div>

            {/* Progress */}
            <div className="mb-6 space-y-2">
                <div className="flex justify-between text-xs font-semibold text-white/70 uppercase tracking-wider">
                    <span>Шаг {currentStep.step_number} из {currentStep.total_steps}</span>
                    <span>{progressPercent}%</span>
                </div>
                <Progress value={progressPercent} className="h-2 bg-white/10" />
            </div>

            {/* Main Content */}
            <Card className="bg-white/10 border-white/20 backdrop-blur-md shadow-xl flex-1 md:flex-none">
                <CardContent className="p-6 md:p-8 flex flex-col h-full">
                    <h2 className="text-xl md:text-2xl font-bold text-white mb-8 whitespace-pre-wrap leading-relaxed">
                        {currentStep.message}
                    </h2>

                    <div className="flex-1 flex flex-col justify-center space-y-4">
                        {/* Single Choice */}
						{/* || currentStep.input_type === 'confirm' */}

                        {(currentStep.input_type === 'single_choice') && (
                            <div className="grid gap-3">
                                {currentStep.options.map(option => (
                                    <div key={option.id} className="flex flex-col gap-2">
										<ButtonOption
											selected={singleChoice === option.id}
											className="p-4"
											onClick={() => setSingleChoice(option.id)}
										>
											<span className="font-medium text-lg">{option.label}</span>
										</ButtonOption>
                                        
                                        {option.id === 'other' && singleChoice === 'other' && (
                                            <Input
                                                value={textInput}
                                                onChange={(e) => setTextInput(e.target.value)}
                                                placeholder="Напиши свой вариант..."
                                                autoFocus
                                                className="bg-white/5 border-white/20 text-white placeholder:text-white/30 h-14 text-lg mt-1 animate-in fade-in slide-in-from-top-2"
                                                onKeyDown={(e) => {
                                                    if (e.key === 'Enter') handleNext()
                                                }}
                                            />
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* Multi Choice */}
                        {currentStep.input_type === 'multi_choice' && (
                            <div className="grid gap-3">
                                {currentStep.options.map(option => {
                                    const isSelected = multiChoice.includes(option.id)
                                    const handleToggle = () => {
                                        if (option.id === 'none') {
                                            setMultiChoice(['none'])
                                        } else {
                                            setMultiChoice(prev => {
                                                const withoutNone = prev.filter(id => id !== 'none')
                                                return isSelected 
                                                    ? withoutNone.filter(id => id !== option.id)
                                                    : [...withoutNone, option.id]
                                            })
                                        }
                                    }
                                    
                                    return (
                                        <div key={option.id} className="flex flex-col gap-2">
											<ButtonOption
												selected={isSelected}
												className="p-4"
												onClick={handleToggle}
												indicator="checkbox"
											>
												<span className="font-medium text-lg">{option.label}</span>
											</ButtonOption>
                                            
                                            {option.id === 'other' && isSelected && (
                                                <Input
                                                    value={textInput}
                                                    onChange={(e) => setTextInput(e.target.value)}
                                                    placeholder="Напиши свой вариант..."
                                                    autoFocus
                                                    className="bg-white/5 border-white/20 text-white placeholder:text-white/30 h-14 text-lg mt-1 animate-in fade-in slide-in-from-top-2"
                                                    onKeyDown={(e) => {
                                                        if (e.key === 'Enter') handleNext()
                                                    }}
                                                />
                                            )}
                                        </div>
                                    )
                                })}
                            </div>
                        )}

                        {/* Text Input */}
                        {currentStep.input_type === 'text_optional' && (
                            <div className="space-y-4">
                                <Input
                                    value={textInput}
                                    onChange={(e) => setTextInput(e.target.value)}
                                    placeholder="Напиши здесь свои комментарии..."
                                    className="bg-white/5 border-white/20 text-white placeholder:text-white/30 h-14 text-lg"
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter') handleNext()
                                    }}
                                />
                                {currentStep.options
									.filter(option => !["skip", "continue"].includes(option.id))
									.map(option => (
										<ButtonOption
											key={option.id}
											// selected={singleChoice === option.id}
											className="p-4"
											onClick={() => {
												setTextInput('')
												submitAnswer('skip')
											}}
											indicator={false}
										>
											<span className="font-medium text-lg">{option.label}</span>
										</ButtonOption>
                                ))}
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>

            {/* Navigation */}
            <div className="flex justify-between items-center mt-6">
                {currentStep.prev_step ? (
                    <Button 
                        variant="outline" 
                        size="lg"
                        onClick={handleBack}
                        disabled={submitting}
                        className="border-white/20 text-white hover:bg-white/10 bg-transparent rounded-xl"
                    >
                        <ArrowLeft className="w-5 h-5 mr-2" />
                        Назад
                    </Button>
                ) : (
                    <div /> // Placeholder for flex spacing
                )}

                <Button 
                    size="lg"
                    onClick={handleNext}
                    disabled={isNextDisabled()}
                    className="bg-white text-primary hover:bg-white/90 font-bold rounded-xl px-8 shadow-lg shadow-white/10"
                >
                    {submitting ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                        <>
                            Продолжить
                            <ArrowRight className="w-5 h-5 ml-2" />
                        </>
                    )}
                </Button>
            </div>
        </div>
    )
}
