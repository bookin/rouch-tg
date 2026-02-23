import { useState, useEffect } from 'react'
import { 
  getProjectSetup, 
  activateProject, 
  createPartner, 
  ProjectSetupResponse, 
  PartnerOut,
  ProjectStatusResponse,
  getPartners
} from '../api/client'
import { Check, ChevronLeft, ChevronRight, Globe, Home, Loader2, Rocket, Sprout, UserPlus } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Card, CardContent, CardFooter, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'

interface Props {
  historyId: string
  onComplete: (projectData: ProjectStatusResponse) => void
  onCancel: () => void
}

type Step = 'intro' | 'source' | 'ally' | 'protege' | 'world' | 'finish'

export default function PartnerWizard({ historyId, onComplete, onCancel }: Props) {
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [setupData, setSetupData] = useState<ProjectSetupResponse | null>(null)
  const [step, setStep] = useState<Step>('intro')
  const [selections, setSelections] = useState<Record<string, string[]>>({
    source: [],
    ally: [],
    protege: [],
    world: []
  })
  
  const [isolationSettings, setIsolationSettings] = useState<Record<string, { is_isolated: boolean }>>({
    source: { is_isolated: false },
    ally: { is_isolated: false },
    protege: { is_isolated: false },
    world: { is_isolated: false }
  })

  // For creating new partner
  const [newPartnerName, setNewPartnerName] = useState('')
  const [newPartnerContactType, setNewPartnerContactType] = useState<'physical' | 'online'>('physical')
  const [isCreating, setIsCreating] = useState(false)

  useEffect(() => {
    loadSetup()
  }, [historyId])

  const loadSetup = async () => {
    try {
      setLoading(true)
      const data = await getProjectSetup(historyId)
      setSetupData(data)
    } catch (e) {
      console.error('Failed to load project setup', e)
      alert('Ошибка загрузки данных. Попробуйте позже.')
      onCancel()
    } finally {
      setLoading(false)
    }
  }

  const getGuide = (category: string) => {
    return setupData?.partner_selection_guide?.find((g: any) => g.category === category)
  }

  const handleNext = async () => {
    if (step === 'intro') setStep('source')
    else if (step === 'source') setStep('ally')
    else if (step === 'ally') setStep('protege')
    else if (step === 'protege') setStep('world')
    else if (step === 'world') {
      await finishSetup()
    }
  }

  const handleBack = () => {
    if (step === 'source') setStep('intro')
    else if (step === 'ally') setStep('source')
    else if (step === 'protege') setStep('ally')
    else if (step === 'world') setStep('protege')
  }

  const togglePartner = (category: string, id: string) => {
    setSelections((prev: Record<string, string[]>) => {
      const current = prev[category] || []
      const updated = current.includes(id) 
        ? current.filter((p: string) => p !== id)
        : [...current, id]
      
      return { ...prev, [category]: updated }
    })
  }

  const handleCreatePartner = async (category: string) => {
    if (!newPartnerName.trim()) return
    
    try {
      setIsCreating(true)
      // fetch partners to find group
      const partnersData = await getPartners()
      const group = partnersData.groups.find((g: any) => g.universal_category === category)
      
      if (!group) {
        alert('Ошибка: группа для этой категории не найдена')
        return
      }

      const newP = await createPartner({
        name: newPartnerName,
        group_id: group.id,
        contact_type: newPartnerContactType
      })
      
      if (newP.success) {
        // Add to local state
        const p: PartnerOut = {
          id: newP.partner_id,
          name: newPartnerName,
          group_id: group.id,
          contact_type: newPartnerContactType
        }
        
        setSetupData((prev: ProjectSetupResponse | null) => {
          if (!prev) return null
          const catList = prev.user_partners[category] || []
          return {
            ...prev,
            user_partners: {
              ...prev.user_partners,
              [category]: [...catList, p]
            }
          }
        })
        
        // Auto select
        togglePartner(category, newP.partner_id)
        setNewPartnerName('')
        setNewPartnerContactType('physical')
      }
      
    } catch (e) {
      console.error(e)
      alert('Не удалось создать партнера')
    } finally {
      setIsCreating(false)
    }
  }

  const finishSetup = async () => {
    try {
      setSubmitting(true)
      const res = await activateProject({
        history_id: historyId,
        project_partners: selections,
        isolation_settings: isolationSettings
      })
      onComplete(res)
    } catch (e) {
      console.error(e)
      alert('Не удалось активировать проект')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading || !setupData) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[40vh] gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className=" text-sm">Подготавливаем мастер выбора партнеров...</p>
      </div>
    )
  }

  if (step === 'intro') {
    return (
      <Card>
        <CardHeader className="text-center pb-2">
          <div className="mx-auto bg-primary backdrop-blur-main w-16 h-16 rounded-full flex items-center justify-center mb-4 border border-primary/20">
            <Sprout className="h-8 w-8 text-white" />
          </div>
          <CardTitle className="text-2xl">Почва для семян</CardTitle>
          <CardDescription className="text-base pt-2">
            Чтобы достичь цели <span className="font-semibold text-white/60">"{setupData.problem}"</span>, нам нужно посадить ментальные семена.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-center space-y-4 pt-4">
          <p className="">
            Семена нельзя посадить в пустоту — нужны другие люди. Сейчас мы выберем 4 кармических партнеров для твоего проекта.
          </p>
        </CardContent>
        <CardFooter className="flex gap-3 pt-6">
          <Button variant="outline" className="flex-1" onClick={onCancel}>
            Отмена
          </Button>
          <Button className="flex-[2]" onClick={handleNext}>
            Начать выбор
            <ChevronRight className="ml-2 h-4 w-4" />
          </Button>
        </CardFooter>
      </Card>
    )
  }

  const renderStep = (category: string) => {
    const guide = getGuide(category)
    const partners = setupData.user_partners[category] || []
    const selected = selections[category] || []
    const isIsolated = isolationSettings[category]?.is_isolated || false

    // If no guide found (should not happen with backend fallback), show generic
    const displayTitle = guide?.title || category.toUpperCase()
    const displayDesc = guide?.description || 'Выберите партнера для этой категории'
    const fallbackAdvice = (guide as any)?.fallback_advice || 'Если нет партнера в этой категории, используйте ментальные семена.'

    const handleIsolationToggle = (checked: boolean) => {
      setIsolationSettings(prev => ({
        ...prev,
        [category]: { is_isolated: checked }
      }))
      // If isolated, clear selections
      if (checked) {
        setSelections(prev => ({ ...prev, [category]: [] }))
      }
    }

    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold uppercase tracking-wider ">
              Шаг {['source', 'ally', 'protege', 'world'].indexOf(category) + 1} из 4
            </span>
            <div className="flex gap-1">
              {['source', 'ally', 'protege', 'world'].map((c) => (
                <div 
                  key={c} 
                  className={cn(
                    "h-1.5 w-6 rounded-full backdrop-blur-main",
                    c === category ? "bg-primary" : "bg-white/10"
                  )} 
                />
              ))}
            </div>
          </div>
          <CardTitle className="text-xl">{displayTitle}</CardTitle>
          <CardDescription className="text-base /90">{displayDesc}</CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-6">
          {guide?.examples && guide.examples.length > 0 && (
            <div className="bg-white/40 backdrop-blur-md p-3 rounded-lg text-sm  flex gap-2 border border-white/30 shadow-sm">
              <span className="shrink-0">💡</span>
              <span>Пример: {guide.examples.join(', ')}</span>
            </div>
          )}

          <div className="flex items-center space-x-2 backdrop-blur-main rounded-md border shadow-sm bg-orange-600/20 border-orange-600/40">
            <Checkbox 
              id="isolation-mode" 
              checked={isIsolated}
              onCheckedChange={handleIsolationToggle}
              className="border-orange-400 data-[state=checked]:bg-orange-500 data-[state=checked]:border-orange-500 bg-white/50 h-5 w-5 ml-3"
            />
            <label
              htmlFor="isolation-mode"
              className="w-full  p-3 text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 text-white cursor-pointer select-none"
            >
              У меня нет никого в этой категории
            </label>
          </div>

          {isIsolated ? (
            <div className="p-4 rounded-xl bg-green-50/60 backdrop-blur-main border border-green-100/50 space-y-2 shadow-sm">
              <h4 className="text-sm font-bold text-green-800 flex items-center gap-2">
                <Sprout className="h-4 w-4" />
                Что делать:
              </h4>
              <p className="text-sm text-green-800 leading-relaxed">{fallbackAdvice}</p>
            </div>
          ) : (
            <>
              <div className="space-y-3">
                <div className="text-sm font-semibold">Выбери из списка:</div>
                {partners.length === 0 && (
                  <div className="text-sm  italic pl-2">Пока никого нет</div>
                )}
                <div className="grid gap-2">
                  {partners.map((p: PartnerOut) => {
                    const isSelected = selected.includes(p.id)
                    return (
                      <div 
                        key={p.id}
                        onClick={() => togglePartner(category, p.id)}
                        className={cn(
                          "flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-all backdrop-blur-main bg-white/10 border-white/30 hover:bg-white/20 hover:border-white/50",
                          // isSelected
                          //   ? "border-primary shadow-[0_0_10px_rgba(37,99,235,0.15)]"
                          //   : " "
                        )}
                      >
                        <div className="flex items-center gap-3">
                          <div className={cn(
                            "h-5 w-5 rounded border-2 flex items-center justify-center transition-colors",
                            isSelected 
                              ? "bg-primary border-primary text-primary-foreground" 
                              : "border-white/50 "
                          )}>
                            {isSelected && <Check className="h-3.5 w-3.5" />}
                          </div>
                          <span className="font-medium text-sm">{p.name}</span>
                        </div>
                        
                        {p.contact_type && (
                          <div className="flex items-center gap-1 text-[10px] uppercase tracking-wider font-semibold bg-white/10 px-2 py-1 rounded ">
                            {p.contact_type === 'online' ? <Globe className="h-3 w-3" /> : <Home className="h-3 w-3" />}
                            {p.contact_type === 'online' ? 'Онлайн' : 'Лично'}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>

              <div className="space-y-3 pt-4 border-t">
                <div className="text-sm font-semibold flex items-center gap-2">
                  <UserPlus className="h-4 w-4" />
                  Или добавь нового:
                </div>
                <div className="space-y-3">
                  <Input
                    value={newPartnerName}
                    onChange={(e) => setNewPartnerName(e.target.value)}
                    placeholder="Имя партнера..."
                    className=""
                  />
                  
                  <div className="grid grid-cols-2 gap-3">
                    <Button
                      variant={newPartnerContactType === 'physical' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setNewPartnerContactType('physical')}
                      className="w-full"
                    >
                      <Home className="mr-2 h-3 w-3" />
                      Лично
                    </Button>
                    <Button
                      variant={newPartnerContactType === 'online' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setNewPartnerContactType('online')}
                      className="w-full"
                    >
                      <Globe className="mr-2 h-3 w-3" />
                      Онлайн
                    </Button>
                  </div>

                  <Button 
                    onClick={() => handleCreatePartner(category)}
                    disabled={isCreating || !newPartnerName}
                    className="w-full"
                    size="sm"
                  >
                    {isCreating ? (
                      <>
                        <Loader2 className="mr-2 h-3 w-3 animate-spin" />
                        Создаем...
                      </>
                    ) : 'Добавить и выбрать'}
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>

        <CardFooter className="flex gap-3 pt-2">
          <Button variant="outline" className="flex-1" onClick={handleBack}>
            <ChevronLeft className="mr-2 h-4 w-4" />
            Назад
          </Button>
          <Button className="flex-[2]" onClick={handleNext}>
            {step === 'world' ? (
              <>
                {submitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Rocket className="mr-2 h-4 w-4" />}
                {submitting ? 'Создаем...' : 'Запустить проект'}
              </>
            ) : (
              <>
                Далее
                <ChevronRight className="ml-2 h-4 w-4" />
              </>
            )}
          </Button>
        </CardFooter>
      </Card>
    )
  }

  if (step === 'source') return renderStep('source')
  if (step === 'ally') return renderStep('ally')
  if (step === 'protege') return renderStep('protege')
  if (step === 'world') return renderStep('world')

  return null
}
