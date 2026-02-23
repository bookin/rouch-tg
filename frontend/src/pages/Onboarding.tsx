import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { ArrowRight, Check, ChevronRight, Loader2, Send, User } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

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
}

interface ChatMessage {
    id: string
    type: 'bot' | 'user'
    text: string
    options?: OnboardingOption[]
    showOptions?: boolean
}

export default function Onboarding() {
    const navigate = useNavigate()
    const [messages, setMessages] = useState<ChatMessage[]>([])
    const [currentStep, setCurrentStep] = useState<OnboardingStep | null>(null)
    const [loading, setLoading] = useState(true)
    const [selectedMulti, setSelectedMulti] = useState<string[]>([])
    const [textInput, setTextInput] = useState('')
    const [isTyping, setIsTyping] = useState(false)
    const messagesEndRef = useRef<HTMLDivElement>(null)

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }

    useEffect(() => {
        scrollToBottom()
    }, [messages, isTyping])

    // Start onboarding on mount
    useEffect(() => {
        startOnboarding()
    }, [])

    const startOnboarding = async () => {
        try {
            const response = await api.get('/api/onboarding/start')
            const step = response.data as OnboardingStep

            if (step.completed) {
                navigate('/')
                return
            }

            setCurrentStep(step)
            addBotMessage(step)
            setLoading(false)
        } catch (error) {
            console.error('Failed to start onboarding:', error)
            setLoading(false)
        }
    }

    const addBotMessage = (step: OnboardingStep) => {
        setIsTyping(true)

        setTimeout(() => {
            setIsTyping(false)
            const newMessage: ChatMessage = {
                id: `bot-${Date.now()}`,
                type: 'bot',
                text: step.message,
                options: step.options,
                showOptions: true
            }
            setMessages(prev => [...prev, newMessage])
        }, 400)
    }

    const handleSingleChoice = async (optionId: string, label: string) => {
        if (!currentStep) return

        // Add user message
        setMessages(prev => prev.map(m => ({ ...m, showOptions: false })))
        setMessages(prev => [...prev, {
            id: `user-${Date.now()}`,
            type: 'user',
            text: label
        }])

        await submitAnswer(optionId)
    }

    const handleMultiChoiceToggle = (optionId: string) => {
        setSelectedMulti(prev =>
            prev.includes(optionId)
                ? prev.filter(id => id !== optionId)
                : [...prev, optionId]
        )
    }

    const handleMultiChoiceSubmit = async () => {
        if (!currentStep || selectedMulti.length === 0) return

        const labels = currentStep.options
            .filter(o => selectedMulti.includes(o.id))
            .map(o => o.label)
            .join(', ')

        setMessages(prev => prev.map(m => ({ ...m, showOptions: false })))
        setMessages(prev => [...prev, {
            id: `user-${Date.now()}`,
            type: 'user',
            text: labels
        }])

        await submitAnswer(undefined, selectedMulti)
        setSelectedMulti([])
    }

    const handleTextSubmit = async () => {
        if (!currentStep) return

        const answer = textInput.trim() || 'skip'
        const displayText = textInput.trim() || 'Пропущено'

        setMessages(prev => prev.map(m => ({ ...m, showOptions: false })))
        setMessages(prev => [...prev, {
            id: `user-${Date.now()}`,
            type: 'user',
            text: displayText
        }])

        await submitAnswer(answer)
        setTextInput('')
    }

    const submitAnswer = async (answer?: string, answers?: string[]) => {
        if (!currentStep) return

        try {
            const response = await api.post('/api/onboarding/answer', {
                step: currentStep.step,
                answer,
                answers
            })

            const nextStep = response.data as OnboardingStep
            setCurrentStep(nextStep)

            if (nextStep.completed) {
                setIsTyping(true)
                setTimeout(() => {
                    setIsTyping(false)
                    setMessages(prev => [...prev, {
                        id: `bot-complete`,
                        type: 'bot',
                        text: nextStep.message
                    }])

                    // Redirect after showing completion message
                    setTimeout(() => {
                        navigate('/')
                    }, 2000)
                }, 400)
            } else {
                addBotMessage(nextStep)
            }
        } catch (error) {
            console.error('Failed to submit answer:', error)
        }
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen ">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        )
    }

    return (
        <div className="flex flex-col h-screen bg-transparent font-sans">
            {/* Header */}
            <div className="px-5 py-4 bg-white/30 backdrop-blur-xl border-b border-white/30 flex items-center gap-3 sticky top-0 z-10 shadow-sm">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white shadow-md">
                    <User className="h-5 w-5" />
                </div>
                <div>
                    <div className="font-bold text-sm">Rouch Karma Manager</div>
                    <div className="text-xs  font-medium">
                        {currentStep && `Шаг ${currentStep.step_number} из ${currentStep.total_steps}`}
                    </div>
                </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-none">
                {messages.map(message => (
                    <div 
                        key={message.id} 
                        className={cn(
                            "flex w-full animate-in fade-in slide-in-from-bottom-2 duration-300",
                            message.type === 'user' ? "justify-end" : "justify-start"
                        )}
                    >
                        <div className={cn(
                            "max-w-[85%] px-4 py-3 shadow-sm text-sm leading-relaxed backdrop-blur-main",
                            message.type === 'user'
                                ? "bg-primary text-primary-foreground rounded-2xl rounded-tr-sm shadow-md"
                                : "bg-white/70 border border-white/40 rounded-2xl rounded-tl-sm shadow-sm"
                        )}>
                            {message.text}
                        </div>
                    </div>
                ))}

                {/* Typing indicator */}
                {isTyping && (
                    <div className="flex justify-start animate-in fade-in zoom-in duration-300">
                        <div className="px-4 py-3 rounded-2xl rounded-tl-sm bg-white/50 border border-white/30 flex items-center gap-1.5 h-10 w-16 justify-center backdrop-blur-main">
                            <div className="w-1.5 h-1.5 bg-muted-foreground/40 rounded-full animate-bounce delay-0" />
                            <div className="w-1.5 h-1.5 bg-muted-foreground/40 rounded-full animate-bounce delay-150" />
                            <div className="w-1.5 h-1.5 bg-muted-foreground/40 rounded-full animate-bounce delay-300" />
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Input area */}
            {currentStep && !currentStep.completed && messages.length > 0 && messages[messages.length - 1].showOptions && (
                <div className="p-4 bg-white/60 border-t border-white/30 backdrop-blur-xl shadow-[0_-4px_20px_rgba(0,0,0,0.05)] animate-in slide-in-from-bottom-10 duration-500">
                    
                    {/* Single Choice & Confirm */}
                    {(currentStep.input_type === 'single_choice' || currentStep.input_type === 'confirm') && (
                        <div className="flex flex-col gap-2">
                            {currentStep.options.map(option => (
                                <Button
                                    key={option.id}
                                    variant="outline"
                                    onClick={() => handleSingleChoice(option.id, option.label)}
                                    className="w-full justify-start h-auto py-3.5 text-sm font-medium bg-white/50 hover:bg-primary/10 hover:text-primary border-white/40 hover:border-primary/30 transition-all text-left backdrop-blur-main shadow-sm"
                                >
                                    {option.label}
                                </Button>
                            ))}
                        </div>
                    )}

                    {/* Multi Choice */}
                    {currentStep.input_type === 'multi_choice' && (
                        <div className="flex flex-col gap-2">
                            {currentStep.options.map(option => {
                                const isSelected = selectedMulti.includes(option.id)
                                return (
                                    <Button
                                        key={option.id}
                                        variant="outline"
                                        onClick={() => handleMultiChoiceToggle(option.id)}
                                        className={cn(
                                            "w-full justify-between h-auto py-3.5 text-sm font-medium transition-all group backdrop-blur-main border-white/40 shadow-sm",
                                            isSelected 
                                                ? "bg-primary/10 border-primary text-primary hover:bg-primary/15" 
                                                : "bg-white/50 hover:bg-white/70"
                                        )}
                                    >
                                        {option.label}
                                        <div className={cn(
                                            "w-5 h-5 rounded border flex items-center justify-center transition-colors",
                                            isSelected ? "bg-primary border-primary text-primary-foreground" : "border-muted-foreground/30 bg-white/50"
                                        )}>
                                            {isSelected && <Check className="h-3 w-3" />}
                                        </div>
                                    </Button>
                                )
                            })}
                            <Button
                                onClick={handleMultiChoiceSubmit}
                                disabled={selectedMulti.length === 0}
                                className="w-full mt-2 font-bold shadow-lg shadow-primary/20"
                            >
                                Продолжить
                                <ArrowRight className="ml-2 h-4 w-4" />
                            </Button>
                        </div>
                    )}

                    {/* Text Input */}
                    {currentStep.input_type === 'text_optional' && (
                        <div className="flex gap-2 items-center">
                            <Input
                                type="text"
                                value={textInput}
                                onChange={(e) => setTextInput(e.target.value)}
                                placeholder="Напиши здесь..."
                                className="bg-white/50 border-white/40 focus:bg-white/80 shadow-inner"
                                onKeyDown={(e) => e.key === 'Enter' && handleTextSubmit()}
                            />
                            <Button
                                onClick={handleTextSubmit}
                                size="icon"
                                className={cn(
                                    "shrink-0 transition-all shadow-md",
                                    !textInput.trim() && "opacity-80 bg-secondary hover:bg-secondary/80"
                                )}
                            >
                                {textInput.trim() ? <Send className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                            </Button>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}
