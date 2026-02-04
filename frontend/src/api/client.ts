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

// Add Telegram WebApp authentication interceptor
api.interceptors.request.use((config) => {
  // Get Telegram WebApp initData
  if (window.Telegram?.WebApp) {
    const initData = window.Telegram.WebApp.initData
    if (initData) {
      config.headers.Authorization = initData
    }
  }
  return config
}, (error) => {
  return Promise.reject(error)
})

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
}

export const createPartner = async (payload: PartnerCreatePayload) => {
  const response = await api.post('/api/partners', payload)
  return response.data
}

export const getPractices = async () => {
  const response = await api.get('/api/practices')
  return response.data
}

export const getHabits = async () => {
  const response = await api.get('/api/habits')
  return response.data
}

export const solveProblem = async (problem: string) => {
  const response = await api.post('/api/problem/solve', { problem })
  return response.data
}

export const updateUserFocus = async (focus: string) => {
  const response = await api.patch('/api/me/focus', { focus })
  return response.data
}

export const getProblemsHistory = async () => {
  const response = await api.get('/api/problems/history')
  return response.data
}

export const activateProblem = async (id: string) => {
  const response = await api.post(`/api/problems/${id}/activate`)
  return response.data
}

export const addProblemToCalendar = async (steps: string[]) => {
  const response = await api.post('/api/problem/add-to-calendar', { steps })
  return response.data
}
