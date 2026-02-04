import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'

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
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100vh',
                background: 'var(--tg-theme-bg-color, #fff)'
            }}>
                <div style={{ fontSize: '24px' }}>🧘</div>
            </div>
        )
    }

    return (
        <div style={{
            display: 'flex',
            flexDirection: 'column',
            height: '100vh',
            background: 'var(--tg-theme-bg-color, #fff)'
        }}>
            {/* Header */}
            <div style={{
                padding: '16px 20px',
                background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)',
                borderBottom: '1px solid rgba(0,0,0,0.05)',
                display: 'flex',
                alignItems: 'center',
                gap: '12px'
            }}>
                <div style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '50%',
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '20px'
                }}>
                    🧘
                </div>
                <div>
                    <div style={{ fontWeight: 700, fontSize: '16px' }}>Rouch Karma Manager</div>
                    <div style={{ fontSize: '12px', opacity: 0.6 }}>
                        {currentStep && `Шаг ${currentStep.step_number} из ${currentStep.total_steps}`}
                    </div>
                </div>
            </div>

            {/* Messages */}
            <div style={{
                flex: 1,
                overflowY: 'auto',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px'
            }}>
                {messages.map(message => (
                    <div key={message.id} style={{
                        display: 'flex',
                        justifyContent: message.type === 'user' ? 'flex-end' : 'flex-start'
                    }}>
                        <div style={{
                            maxWidth: '85%',
                            padding: '12px 16px',
                            borderRadius: message.type === 'user'
                                ? '18px 18px 4px 18px'
                                : '18px 18px 18px 4px',
                            background: message.type === 'user'
                                ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                                : 'var(--tg-theme-secondary-bg-color, #f0f0f0)',
                            color: message.type === 'user' ? '#fff' : 'inherit',
                            whiteSpace: 'pre-wrap',
                            lineHeight: 1.5
                        }}>
                            {message.text}
                        </div>
                    </div>
                ))}

                {/* Typing indicator */}
                {isTyping && (
                    <div style={{
                        display: 'flex',
                        justifyContent: 'flex-start'
                    }}>
                        <div style={{
                            padding: '12px 16px',
                            borderRadius: '18px 18px 18px 4px',
                            background: 'var(--tg-theme-secondary-bg-color, #f0f0f0)',
                            display: 'flex',
                            gap: '4px'
                        }}>
                            <span style={{ animation: 'bounce 1.4s infinite', animationDelay: '0s' }}>•</span>
                            <span style={{ animation: 'bounce 1.4s infinite', animationDelay: '0.2s' }}>•</span>
                            <span style={{ animation: 'bounce 1.4s infinite', animationDelay: '0.4s' }}>•</span>
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Input area */}
            {currentStep && !currentStep.completed && messages.length > 0 && messages[messages.length - 1].showOptions && (
                <div style={{
                    padding: '16px',
                    borderTop: '1px solid rgba(0,0,0,0.05)',
                    background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)'
                }}>
                    {currentStep.input_type === 'single_choice' || currentStep.input_type === 'confirm' ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            {currentStep.options.map(option => (
                                <button
                                    key={option.id}
                                    onClick={() => handleSingleChoice(option.id, option.label)}
                                    style={{
                                        padding: '14px 20px',
                                        borderRadius: '12px',
                                        border: 'none',
                                        background: '#fff',
                                        color: 'var(--tg-theme-text-color, #000)',
                                        fontSize: '15px',
                                        fontWeight: 500,
                                        cursor: 'pointer',
                                        boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                                        transition: 'all 0.2s',
                                        textAlign: 'left'
                                    }}
                                >
                                    {option.label}
                                </button>
                            ))}
                        </div>
                    ) : currentStep.input_type === 'multi_choice' ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            {currentStep.options.map(option => (
                                <button
                                    key={option.id}
                                    onClick={() => handleMultiChoiceToggle(option.id)}
                                    style={{
                                        padding: '14px 20px',
                                        borderRadius: '12px',
                                        border: selectedMulti.includes(option.id)
                                            ? '2px solid #667eea'
                                            : '2px solid transparent',
                                        background: selectedMulti.includes(option.id)
                                            ? 'rgba(102, 126, 234, 0.1)'
                                            : '#fff',
                                        color: 'var(--tg-theme-text-color, #000)',
                                        fontSize: '15px',
                                        fontWeight: 500,
                                        cursor: 'pointer',
                                        boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                                        transition: 'all 0.2s',
                                        textAlign: 'left',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '10px'
                                    }}
                                >
                                    <span style={{
                                        width: '20px',
                                        height: '20px',
                                        borderRadius: '4px',
                                        border: '2px solid #667eea',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        background: selectedMulti.includes(option.id) ? '#667eea' : 'transparent',
                                        color: '#fff',
                                        fontSize: '12px'
                                    }}>
                                        {selectedMulti.includes(option.id) && '✓'}
                                    </span>
                                    {option.label}
                                </button>
                            ))}
                            {selectedMulti.length > 0 && (
                                <button
                                    onClick={handleMultiChoiceSubmit}
                                    style={{
                                        padding: '14px 20px',
                                        borderRadius: '12px',
                                        border: 'none',
                                        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                        color: '#fff',
                                        fontSize: '15px',
                                        fontWeight: 600,
                                        cursor: 'pointer',
                                        marginTop: '8px'
                                    }}
                                >
                                    Продолжить →
                                </button>
                            )}
                        </div>
                    ) : currentStep.input_type === 'text_optional' ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                            <input
                                type="text"
                                value={textInput}
                                onChange={(e) => setTextInput(e.target.value)}
                                placeholder="Напиши здесь..."
                                style={{
                                    padding: '14px 16px',
                                    borderRadius: '12px',
                                    border: '1px solid rgba(0,0,0,0.1)',
                                    fontSize: '15px',
                                    outline: 'none'
                                }}
                            />
                            <div style={{ display: 'flex', gap: '8px' }}>
                                <button
                                    onClick={handleTextSubmit}
                                    style={{
                                        flex: 1,
                                        padding: '14px',
                                        borderRadius: '12px',
                                        border: 'none',
                                        background: textInput.trim()
                                            ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                                            : '#ddd',
                                        color: '#fff',
                                        fontSize: '15px',
                                        fontWeight: 600,
                                        cursor: 'pointer'
                                    }}
                                >
                                    {textInput.trim() ? 'Отправить' : 'Пропустить'}
                                </button>
                            </div>
                        </div>
                    ) : null}
                </div>
            )}

            <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0); }
          40% { transform: translateY(-6px); }
        }
      `}</style>
        </div>
    )
}
