import axios from 'axios'

export const TOKEN_KEY = 'boardapp_token'
export const USER_KEY = 'boardapp_user'

export interface CurrentUser {
  id: string
  username: string
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function getCurrentUser(): CurrentUser | null {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw) as CurrentUser
    if (parsed && typeof parsed.id === 'string') return parsed
  } catch {
    // битая запись (например, "[object Object]") — чистим
  }
  localStorage.removeItem(USER_KEY)
  return null
}

/** Если токен есть, а пользователя нет/битый — подтягиваем с сервера. */
export async function ensureUser(): Promise<CurrentUser | null> {
  const existing = getCurrentUser()
  if (existing) return existing
  if (!getToken()) return null
  try {
    const { data } = await api.get<CurrentUser>('/api/auth/me')
    localStorage.setItem(USER_KEY, JSON.stringify(data))
    return data
  } catch {
    return null
  }
}

export function setAuth(token: string, user: CurrentUser) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export const api = axios.create({ baseURL: '/boards' })

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && !location.hash.startsWith('#/login')) {
      clearAuth()
      location.assign('/boardapp/sso/')
    }
    return Promise.reject(err)
  },
)

export function apiError(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail
    if (typeof detail === 'string') return detail
  }
  return 'Что-то пошло не так, попробуйте ещё раз'
}
