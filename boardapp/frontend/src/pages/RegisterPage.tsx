import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, apiError, setAuth, type CurrentUser } from '../api'

export default function RegisterPage() {
  const nav = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const { data } = await api.post<{ token: string; user: CurrentUser }>(
        '/api/auth/register',
        { username, password },
      )
      setAuth(data.token, data.user)
      nav('/')
    } catch (err) {
      setError(apiError(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={submit}>
        <h1>Регистрация</h1>
        <input
          autoFocus
          placeholder="Имя пользователя (3–32 символа)"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <input
          type="password"
          placeholder="Пароль (минимум 6 символов)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error && <div className="error">{error}</div>}
        <button disabled={busy || !username || !password}>
          {busy ? 'Создаём…' : 'Создать аккаунт'}
        </button>
        <p className="hint">
          Уже есть аккаунт? <Link to="/login">Войти</Link>
        </p>
      </form>
    </div>
  )
}
