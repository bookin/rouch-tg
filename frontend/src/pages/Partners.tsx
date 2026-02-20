import { FormEvent, useEffect, useMemo, useState } from 'react'
import { createPartner, getPartners, PartnerCreatePayload } from '../api/client'
import { Users, UserPlus, NotebookPen, Loader2, Home, Globe } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'

interface PartnerGroup {
  id: string
  name: string
  icon: string
  description: string
  universal_category?: string
  is_default: boolean
}

interface Partner {
  id: string
  name: string
  group_id: string
  telegram_username?: string
  phone?: string
  notes?: string
  contact_type?: 'physical' | 'online'
}

const CATEGORY_LABELS: Record<string, string> = {
  source: 'Источник',
  ally: 'Соратник',
  protege: 'Подопечный',
  world: 'Внешний мир'
}

const CATEGORY_DESCRIPTIONS: Record<string, string> = {
  source: 'Те, кто дает ресурсы (Родители, учителя, менторы)',
  ally: 'Те, кто помогает в делах (Коллеги, партнеры, супруги)',
  protege: 'Те, кто зависит от тебя (Клиенты, дети, подчиненные)',
  world: 'Далекие люди или конкуренты'
}

const CATEGORY_COLORS: Record<string, string> = {
  source: 'bg-blue-100 text-blue-700 border-blue-200',
  ally: 'bg-green-100 text-green-700 border-green-200',
  protege: 'bg-amber-100 text-amber-700 border-amber-200',
  world: 'bg-slate-100 text-slate-700 border-slate-200'
}

const CATEGORY_ORDER = ['source', 'ally', 'protege', 'world']

export default function Partners() {
  const [loading, setLoading] = useState(true)
  const [groups, setGroups] = useState<PartnerGroup[]>([])
  const [partners, setPartners] = useState<Partner[]>([])
  const [error, setError] = useState<string | null>(null)

  const [newPartnerName, setNewPartnerName] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('source')
  const [newPartnerNotes, setNewPartnerNotes] = useState('')
  const [newPartnerContactType, setNewPartnerContactType] = useState<'physical' | 'online'>('physical')

  // State to toggle notes visibility on click (mobile friendly)
  const [activeNoteId, setActiveNoteId] = useState<string | null>(null)

  const load = async () => {
    try {
      setError(null)
      setLoading(true)
      const data = await getPartners()
      setGroups(data.groups || [])
      setPartners(data.partners || [])
    } catch (e: any) {
      setError(e?.message || 'Failed to load partners')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Helpers to resolve group from category
  const getGroupByCategory = (cat: string) => {
    return groups.find(g => g.universal_category === cat) || groups[0]
  }

  const partnersByCategory = useMemo(() => {
    const map: Record<string, Partner[]> = { source: [], ally: [], protege: [], world: [] }
    
    // Create lookup for group -> category
    const groupCatMap = new Map<string, string>()
    groups.forEach(g => {
      if (g.universal_category) groupCatMap.set(g.id, g.universal_category)
    })

    partners.forEach(p => {
      const cat = groupCatMap.get(p.group_id) || 'world'
      if (!map[cat]) map[cat] = []
      map[cat].push(p)
    })
    
    return map
  }, [groups, partners])

  const onCreatePartner = async (e: FormEvent) => {
    e.preventDefault()
    if (!newPartnerName.trim()) return

    const targetGroup = getGroupByCategory(selectedCategory)
    if (!targetGroup) {
      setError('Группа для этой категории не найдена')
      return
    }

    const payload: PartnerCreatePayload = {
      name: newPartnerName.trim(),
      group_id: targetGroup.id,
      notes: newPartnerNotes.trim() || undefined,
      contact_type: newPartnerContactType
    }

    try {
      setError(null)
      await createPartner(payload)
      setNewPartnerName('')
      setNewPartnerNotes('')
      setNewPartnerContactType('physical')
      await load()
    } catch (err: any) {
      setError(err?.message || 'Failed to create partner')
    }
  }

  if (loading && groups.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-muted-foreground text-sm">Загружаем твоё окружение...</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6 p-4 max-w-5xl mx-auto w-full pb-24">
      <div className="space-y-1 mt-2">
        <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-3">
          <Users className="h-8 w-8 text-primary" />
          Партнёры
        </h1>
        <p className="text-muted-foreground leading-relaxed">
          Твои партнеры — это почва, в которую ты сажаешь семена для достижения своих целей.
        </p>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm font-medium border border-destructive/20">
          {error}
        </div>
      )}

      {/* Partners List Grouped by Category */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {CATEGORY_ORDER.map(cat => {
          const catPartners = partnersByCategory[cat] || []
          const groupInfo = getGroupByCategory(cat)
          
          return (
            <Card key={cat} className="border-none shadow-sm overflow-hidden">
              <div className={cn("h-1 w-full", CATEGORY_COLORS[cat].split(' ')[0])} />
              <CardHeader className="pb-3 pt-5 px-5">
                <div className="flex items-center gap-3">
                  <div className={cn(
                    "h-10 w-10 rounded-full flex items-center justify-center text-lg shadow-sm border",
                    CATEGORY_COLORS[cat]
                  )}>
                    {groupInfo?.icon || '👤'}
                  </div>
                  <div>
                    <CardTitle className="text-lg">{CATEGORY_LABELS[cat]}</CardTitle>
                    <CardDescription className="text-xs mt-1">
                      {CATEGORY_DESCRIPTIONS[cat]}
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="px-5 pb-5 pt-0">
                <div className="grid gap-2">
                  {catPartners.length === 0 && (
                    <div className="text-sm text-muted-foreground/60 italic py-2 text-center bg-secondary/30 rounded-lg border border-dashed border-secondary">
                      Пока никого нет в этой категории
                    </div>
                  )}
                  {catPartners.map(p => (
                    <div 
                      key={p.id} 
                      className="relative flex items-center justify-between p-3 rounded-lg bg-card border hover:border-primary/30 transition-colors shadow-sm"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-foreground">{p.name}</span>
                        {p.contact_type && (
                          <div className="text-[10px] bg-secondary px-1.5 py-0.5 rounded text-muted-foreground flex items-center gap-1">
                            {p.contact_type === 'online' ? <Globe className="h-3 w-3" /> : <Home className="h-3 w-3" />}
                          </div>
                        )}
                      </div>
                      
                      {p.notes && (
                        <>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              setActiveNoteId(activeNoteId === p.id ? null : p.id)
                            }}
                            className={cn(
                              "p-1.5 rounded-full transition-colors",
                              activeNoteId === p.id ? "bg-primary/10 text-primary" : "text-muted-foreground/50 hover:text-primary hover:bg-primary/5"
                            )}
                          >
                            <NotebookPen className="h-4 w-4" />
                          </button>
                          
                          {activeNoteId === p.id && (
                            <div className="absolute right-0 top-12 z-20 w-48 p-3 bg-popover text-popover-foreground text-xs rounded-md shadow-md border animate-in fade-in zoom-in-95 duration-200">
                              <div className="font-semibold mb-1 text-primary">Заметки:</div>
                              {p.notes}
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Add Partner Form */}
      <Card className="border-primary/20 shadow-md">
        <CardHeader className="pb-3 bg-secondary/30">
          <CardTitle className="flex items-center gap-2 text-lg text-primary">
            <UserPlus className="h-5 w-5" />
            Добавить партнёра
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-5 space-y-4">
          <form onSubmit={onCreatePartner} className="space-y-4">
            
            <div className="space-y-2">
              <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                Категория
              </label>
              <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-none mask-linear-fade">
                {CATEGORY_ORDER.map(cat => {
                  const isActive = selectedCategory === cat
                  const g = getGroupByCategory(cat)
                  return (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => setSelectedCategory(cat)}
                      className={cn(
                        "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-all whitespace-nowrap",
                        isActive 
                          ? cn("ring-1 ring-offset-1", CATEGORY_COLORS[cat])
                          : "bg-background border-input hover:bg-accent hover:text-accent-foreground text-muted-foreground"
                      )}
                    >
                      <span>{g?.icon}</span>
                      <span>{CATEGORY_LABELS[cat].split('(')[0]}</span>
                    </button>
                  )
                })}
              </div>
            </div>

            <div className="space-y-2">
              <Input
                value={newPartnerName}
                onChange={(e) => setNewPartnerName(e.target.value)}
                placeholder="Имя партнёра"
                className="bg-background"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-3">
              <Button
                type="button"
                variant={newPartnerContactType === 'physical' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setNewPartnerContactType('physical')}
                className="w-full"
              >
                <Home className="mr-2 h-3 w-3" />
                Лично
              </Button>
              <Button
                type="button"
                variant={newPartnerContactType === 'online' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setNewPartnerContactType('online')}
                className="w-full"
              >
                <Globe className="mr-2 h-3 w-3" />
                Онлайн
              </Button>
            </div>
            
            <div className="space-y-2">
              <Textarea
                value={newPartnerNotes}
                onChange={(e) => setNewPartnerNotes(e.target.value)}
                placeholder="Заметки (что он любит, день рождения...)"
                className="resize-none min-h-[80px] bg-background"
              />
            </div>

            <Button 
              type="submit" 
              className="w-full" 
              disabled={!newPartnerName.trim()}
            >
              Сохранить партнёра
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
