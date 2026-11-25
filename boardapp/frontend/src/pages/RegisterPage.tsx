import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, apiError, setAuth, type CurrentUser } from '../api'
import { useDocumentTitle } from '../useDocumentTitle'

export default function RegisterPage() {
  const nav = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  useDocumentTitle('Регистрация — Доски')

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
        <label htmlFor="register-username">Имя пользователя</label>
        <input
          id="register-username"
          name="username"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          required
          minLength={3}
          maxLength={32}
          autoFocus
          aria-describedby="register-username-hint"
          placeholder="Имя пользователя (3–32 символа)"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <span id="register-username-hint" className="field-hint">3–32 символа: латинские буквы, цифры, точка, дефис, подчёркивание</span>
        <label htmlFor="register-password">Пароль</label>
        <input
          id="register-password"
          name="password"
          type={showPassword ? 'text' : 'password'}
          autoComplete="new-password"
          required
          minLength={6}
          aria-describedby="register-password-hint"
          placeholder="Пароль (минимум 6 символов)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <span id="register-password-hint" className="field-hint">Минимум 6 символов</span>
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
          {busy ? 'Создаём…' : 'Создать аккаунт'}
        </button>
        <p className="hint">
          Уже есть аккаунт? <Link to="/login">Войти</Link>
        </p>
      </form>
    </div>
  )
}
