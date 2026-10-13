import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, apiError, clearAuth, ensureUser, type CurrentUser } from '../api'
import type { BoardsList } from './BoardsPageTypes'

export default function BoardsPage() {
  const nav = useNavigate()
  const [me, setMe] = useState<CurrentUser | null>(null)
  const [data, setData] = useState<BoardsList | null>(null)
  const [newTitle, setNewTitle] = useState('')
  const [renaming, setRenaming] = useState<string | null>(null)
  const [renameTitle, setRenameTitle] = useState('')
  const [error, setError] = useState('')

  async function load() {
    try {
      const { data } = await api.get<BoardsList>('/api/boards')
      setData(data)
    } catch (err) {
      setError(apiError(err))
    }
  }

  useEffect(() => {
    ensureUser().then(setMe)
    load()
  }, [])

  async function createBoard() {
    if (!newTitle.trim()) return
    try {
      await api.post('/api/boards', { title: newTitle.trim() })
      setNewTitle('')
      await load()
    } catch (err) {
      setError(apiError(err))
    }
  }

  async function removeBoard(id: string, title: string) {
    if (!confirm(`Удалить доску «${title}»? Действие необратимо.`)) return
    try {
      await api.delete(`/api/boards/${id}`)
      await load()
    } catch (err) {
      setError(apiError(err))
    }
  }

  async function renameBoard(id: string) {
    if (!renameTitle.trim()) return
    try {
      await api.patch(`/api/boards/${id}`, { title: renameTitle.trim() })
      setRenaming(null)
      await load()
    } catch (err) {
      setError(apiError(err))
    }
  }

  return (
    <div className="page">
      <div className="page-head">
        <h1>Мои доски</h1>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <span className="hint">{me?.username}</span>
          <button
            className="btn ghost"
            onClick={() => {
              clearAuth()
              nav('/login')
            }}
          >
            Выйти
          </button>
        </div>
      </div>

      <div className="create-row">
        <input
          placeholder="Название новой доски"
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && createBoard()}
        />
        <button className="btn" onClick={createBoard}>
          Создать
        </button>
      </div>

      {error && <div className="error" style={{ marginTop: 12 }}>{error}</div>}

      <div className="boards-section">
        <h2>Мои доски</h2>
        {(data?.own ?? []).map((b) => (
          <div key={b.id} className="board-row">
            {renaming === b.id ? (
              <>
                <input
                  autoFocus
                  value={renameTitle}
                  onChange={(e) => setRenameTitle(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') renameBoard(b.id)
                    if (e.key === 'Escape') setRenaming(null)
                  }}
                  style={{ flex: 1, background: 'var(--panel2)', border: '1px solid var(--border)', borderRadius: 6, padding: '6px 10px', color: 'var(--text)' }}
                />
                <button className="btn" onClick={() => renameBoard(b.id)}>ОК</button>
                <button className="btn ghost" onClick={() => setRenaming(null)}>Отмена</button>
              </>
            ) : (
              <>
                <Link to={`/board/${b.id}`} className="title">{b.title}</Link>
                <span className="role-badge">owner</span>
                <button
                  className="btn ghost"
                  onClick={() => {
                    setRenaming(b.id)
                    setRenameTitle(b.title)
                  }}
                >
                  Переименовать
                </button>
                <button className="btn ghost" onClick={() => removeBoard(b.id, b.title)}>
                  Удалить
                </button>
              </>
            )}
          </div>
        ))}
        {data && data.own.length === 0 && <p className="hint">Пока нет ни одной доски — создайте первую.</p>}
      </div>

      <div className="boards-section">
        <h2>Доступные мне</h2>
        {(data?.shared ?? []).map((b) => (
          <div key={b.id} className="board-row">
            <Link to={`/board/${b.id}`} className="title">{b.title}</Link>
            <span className="role-badge">{b.role}</span>
          </div>
        ))}
        {data && data.shared.length === 0 && <p className="hint">Вам пока не дали доступ к чужим доскам.</p>}
      </div>
    </div>
  )
}
