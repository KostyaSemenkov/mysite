import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, apiError, setAuth, type CurrentUser } from '../api'
import { useDocumentTitle } from '../useDocumentTitle'

export default function LoginPage() {
  const nav = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  useDocumentTitle('Вход — Доски')

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const { data } = await api.post<{ token: string; user: CurrentUser }>(
        '/api/auth/login',
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
        <h1>Вход</h1>
        <label htmlFor="login-username">Имя пользователя</label>
        <input
          id="login-username"
          name="username"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          required
          autoFocus
          placeholder="Имя пользователя"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <label htmlFor="login-password">Пароль</label>
        <input
          id="login-password"
          name="password"
          type={showPassword ? 'text' : 'password'}
          autoComplete="current-password"
          required
          placeholder="Пароль"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button
          type="button"
          className="password-toggle"
          aria-pressed={showPassword}
          onClick={() => setShowPassword(!showPassword)}
        >
          {showPassword ? 'Скрыть пароль' : 'Показать пароль'}
        </button>
        {error && <div className="error" role="alert">{error}</div>}
        <button type="submit" disabled={busy || !username || !password} aria-busy={busy}>
          {busy ? 'Входим…' : 'Войти'}
        </button>
        <p className="hint">
          Уже есть аккаунт на сайте? <a href="/boardapp/sso/">Войти через сайт</a>
        </p>
        <p className="hint">
          Нет аккаунта? <Link to="/register">Зарегистрироваться</Link>
        </p>
      </form>
    </div>
  )
}
