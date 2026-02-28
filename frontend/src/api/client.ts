import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || ''
console.log('API URL:', API_URL)
// Create axios instance
export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Hybrid auth interceptor: Telegram initData OR JWT Bearer token
api.interceptors.request.use((config) => {
  // 1. Try Telegram WebApp initData first
  if (window.Telegram?.WebApp) {
    const initData = window.Telegram.WebApp.initData
    if (initData) {
      config.headers.Authorization = initData
      return config
    }
  }
  // 2. Fallback to JWT token from localStorage
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}, (error) => {
  return Promise.reject(error)
})

// Handle 401 responses - clear token and redirect to login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const isTelegram = !!window.Telegram?.WebApp?.initData
      if (!isTelegram) {
        localStorage.removeItem('auth_token')
        // Don't redirect if already on login page
        if (!window.location.pathname.includes('/login')) {
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(error)
  }
)

// ===== Auth API =====

export const isTelegramContext = (): boolean => {
  return !!window.Telegram?.WebApp?.initData
}

export const getStoredToken = (): string | null => {
  return localStorage.getItem('auth_token')
}

export const isAuthenticated = (): boolean => {
  return isTelegramContext() || !!getStoredToken()
}

export interface LoginPayload {
  username: string // email
  password: string
}

export interface RegisterPayload {
  email: string
  password: string
  first_name: string
  occupation?: string
}

export const loginUser = async (payload: LoginPayload) => {
  const formData = new URLSearchParams()
  formData.append('username', payload.username)
  formData.append('password', payload.password)
  const response = await api.post('/auth/jwt/login', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  })
  const { access_token } = response.data
  localStorage.setItem('auth_token', access_token)
  return response.data
}

export const registerUser = async (payload: RegisterPayload) => {
  const response = await api.post('/auth/register', payload)
  return response.data
}

export const logoutUser = () => {
  localStorage.removeItem('auth_token')
}

// API methods
export const getUser = async () => {
  const response = await api.get('/api/me')
  return response.data
}

export const getCalendarData = async (startDate: Date, endDate: Date) => {
  const response = await api.get('/api/calendar/data', {
    params: {
      start_date: startDate.toISOString().split('T')[0],
      end_date: endDate.toISOString().split('T')[0]
    }
  })
  return response.data
}

export const getCalendarStats = async (startDate: Date, endDate: Date) => {
  const response = await api.get('/api/calendar/stats', {
    params: {
      start_date: startDate.toISOString().split('T')[0],
      end_date: endDate.toISOString().split('T')[0]
    }
  })
  return response.data
}

export const getDailyQuote = async () => {
  const response = await api.get('/api/quote/daily')
  return response.data
}

export const getDailyActions = async () => {
  const response = await api.get('/api/daily/actions')
  return response.data
}

export const toggleDailyAction = async (id: string, completed: boolean) => {
  const response = await api.patch(`/api/daily/actions/${id}`, { completed })
  return response.data
}

export const getSeeds = async (limit: number = 50) => {
  const response = await api.get('/api/seeds', { params: { limit } })
  return response.data
}

export interface SeedCreatePayload {
  action_type?: string
  description: string
  partner_group?: string
  intention_score?: number
  emotion_level?: number
  understanding?: boolean
  estimated_maturation_days?: number
  strength_multiplier?: number
}

export const createSeed = async (payload: SeedCreatePayload) => {
  const response = await api.post('/api/seeds', payload)
  return response.data
}

export interface CoffeeTodaySeed {
  id: string
  timestamp: string
  action_type: string
  description: string
  partner_group: string
  intention_score: number
  emotion_level: number
  strength_multiplier: number
  estimated_maturation_days: number
  rejoice_count?: number
  last_rejoiced_at?: string | null
}

export interface CoffeeTodayTask {
  id: string
  description: string
  why?: string | null
  group?: string | null
  completed: boolean
}

export interface CoffeeTodayDailyPlan {
  id: string
  day_number: number
  focus_quality?: string | null
  tasks: CoffeeTodayTask[]
  is_completed: boolean
}

export interface CoffeeTodaySession {
  id: string
  current_step: number
  notes_draft?: string | null
  notes?: string | null
  started_at?: string | null
  completed_at?: string | null
  rejoiced_seed_ids: string[]
}

export interface CoffeeTodayResponse {
  has_active_project: boolean
  local_date: string
  utc_start: string
  utc_end: string
  session: CoffeeTodaySession | null
  seeds: CoffeeTodaySeed[]
  daily_plan: CoffeeTodayDailyPlan | null
}

export const getCoffeeToday = async () => {
  const response = await api.get<CoffeeTodayResponse>('/api/coffee/today')
  return response.data
}

export interface CoffeeProgressPayload {
  current_step?: number
  notes_draft?: string
  rejoiced_seed_ids?: string[]
}

export const saveCoffeeProgress = async (payload: CoffeeProgressPayload) => {
  const response = await api.post('/api/coffee/progress', payload)
  return response.data
}

export interface CoffeeCompletePayload {
  rejoiced_seed_ids: string[]
  notes?: string
  complete_project_day?: boolean
  completed_task_ids?: string[]
}

export const completeCoffee = async (payload: CoffeeCompletePayload) => {
  const response = await api.post('/api/coffee/complete', payload)
  return response.data
}

export const getPartners = async () => {
  const response = await api.get('/api/partners')
  return response.data
}

export interface PartnerCreatePayload {
  name: string
  group_id: string
  telegram_username?: string
  phone?: string
  notes?: string
  contact_type?: 'physical' | 'online'
}

export const createPartner = async (payload: PartnerCreatePayload) => {
  const response = await api.post('/api/partners', payload)
  return response.data
}

export const getPractices = async () => {
  const response = await api.get('/api/practices')
  return response.data
}

export interface SolveProblemPayload {
  problem: string
  session_id?: string
  diagnostic_answer?: string
}

export const solveProblem = async (payload: SolveProblemPayload) => {
  const response = await api.post('/api/problem/solve', payload)
  return response.data
}

export const getProblemsHistory = async () => {
  const response = await api.get('/api/problems/history')
  return response.data
}

export const addProblemToCalendar = async (steps: string[]) => {
  const response = await api.post('/api/problem/add-to-calendar', { steps })
  return response.data
}

export interface PartnerOut {
  id: string
  name: string
  group_id: string
  telegram_username?: string
  phone?: string
  notes?: string
  contact_type?: 'physical' | 'online'
}

export interface ProjectDailyTask {
  id: string
  description: string
  why?: string | null
  group?: string | null
  completed: boolean
}

export interface ProjectSetupResponse {
  problem: string
  partner_selection_guide?: Array<{
    category: string
    title: string
    description: string
    examples: string[]
  }>
  user_partners: Record<string, PartnerOut[]>
}

export const getProjectSetup = async (historyId: string) => {
  const response = await api.get<ProjectSetupResponse>(`/api/projects/setup/${historyId}`)
  return response.data
}

export interface ProjectActivatePayload {
  history_id: string
  duration_days?: number
  isolation_settings?: Record<string, { is_isolated: boolean }>
  project_partners?: Record<string, string[]>
}

export interface ProjectStatusResponse {
  has_active_project: boolean
  project?: {
    id: string
    problem: string
    day_number: number
    duration_days: number
    strategy: {
      root_cause?: string
      stop_action?: string
      start_action?: string
      grow_action?: string
      success_tip?: string
      problem_text?: string
    }
    partners?: Record<string, string[]>
    history_id?: string
    isolation_settings?: Record<string, { is_isolated: boolean }>
  }
  daily_plan?: {
    id: string
    day_number: number
    focus_quality: string
    tasks: ProjectDailyTask[]
    is_completed: boolean
  }
}

export const activateProject = async (payload: ProjectActivatePayload) => {
  const response = await api.post<ProjectStatusResponse>('/api/projects/activate', payload)
  return response.data
}

export const getActiveProject = async () => {
  const response = await api.get<ProjectStatusResponse>('/api/projects/active')
  return response.data
}

export interface DailyCompletePayload {
  plan_id: string
  completed_tasks: string[]
  notes?: string
}

export const completeDailyProjectPlan = async (payload: DailyCompletePayload) => {
  const response = await api.post('/api/projects/daily/complete', payload)
  return response.data
}

// Practice Progress API
export interface PracticeProgress {
  practice_id: string
  practice_name: string
  practice_category: string
  practice_duration: number
  habit_score: number
  streak_days: number
  total_completions: number
  last_completed?: string
  is_habit: boolean
  is_active: boolean
  is_hidden: boolean
  can_complete_today: boolean
  habit_min_streak_days: number
  habit_min_score: number
}

export interface Practice {
  id: string
  name: string
  category: string
  description: string
  duration: number
  difficulty: number
  physical_intensity: string
  requires_morning: boolean
  requires_silence: boolean
  max_completions_per_day: number
  steps: string[]
  contraindications: string[]
  benefits: string
  tags: string[]
}

export interface PracticeCompleteRequest {
  emotion_score?: number
}

export const startPracticeTracking = async (practiceId: string) => {
  const response = await api.post(`/api/practices/${practiceId}/start`)
  return response.data
}

export const completePractice = async (practiceId: string, emotionScore: number = 5) => {
  const response = await api.post(`/api/practices/${practiceId}/complete`, {
    emotion_score: emotionScore
  })
  return response.data
}

export const getPracticesProgress = async (): Promise<{ progress: PracticeProgress[] }> => {
  const response = await api.get('/api/practices/progress')
  return response.data
}

export const getPracticeRecommendations = async () => {
  const response = await api.get('/api/practices/recommend')
  return response.data
}

// Practice Management API (M3)
export const pausePractice = async (practiceId: string) => {
  const response = await api.post(`/api/practices/${practiceId}/pause`)
  return response.data
}

export const resumePractice = async (practiceId: string) => {
  const response = await api.post(`/api/practices/${practiceId}/resume`)
  return response.data
}

export const hidePractice = async (practiceId: string) => {
  const response = await api.post(`/api/practices/${practiceId}/hide`)
  return response.data
}

export const resetPractice = async (practiceId: string) => {
  const response = await api.post(`/api/practices/${practiceId}/reset`)
  return response.data
}

export const deletePractice = async (practiceId: string) => {
  const response = await api.delete(`/api/practices/${practiceId}`)
  return response.data
}
