import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, apiError, clearAuth, ensureUser, type CurrentUser } from '../api'
import ConfirmDialog from '../components/ConfirmDialog'
import { useDocumentTitle } from '../useDocumentTitle'
import type { BoardsList } from './BoardsPageTypes'

export default function BoardsPage() {
  const nav = useNavigate()
  const [me, setMe] = useState<CurrentUser | null>(null)
  const [data, setData] = useState<BoardsList | null>(null)
  const [newTitle, setNewTitle] = useState('')
  const [renaming, setRenaming] = useState<string | null>(null)
  const [renameTitle, setRenameTitle] = useState('')
  const [error, setError] = useState('')
  // доска, которую пользователь собирается удалить (ждёт подтверждения в диалоге)
  const [pendingDelete, setPendingDelete] = useState<{ id: string; title: string } | null>(null)
  useDocumentTitle('Мои доски — Доски')

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

  async function removeBoard(id: string) {
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
        <div className="page-head-user">
          <span className="hint">{me?.username}</span>
          <button
            type="button"
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

      {/* обычная форма: Enter в поле создаёт доску, а Enter при наборе IME — нет */}
      <form
        className="create-row"
        onSubmit={(e) => {
          e.preventDefault()
          void createBoard()
        }}
      >
        <label htmlFor="new-board-title" className="visually-hidden">Название новой доски</label>
        <input
          id="new-board-title"
          name="title"
          autoComplete="off"
          placeholder="Название новой доски"
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
        />
        <button type="submit" className="btn" disabled={!newTitle.trim()}>Создать</button>
      </form>

      {error && <div className="error page-error" role="alert">{error}</div>}

      <div className="boards-section">
        <h2>Мои доски</h2>
        <div className="boards-grid">
        {(data?.own ?? []).map((b) => (
          <div key={b.id} className="board-card">
            {renaming === b.id ? (
              <>
                <input
                  autoFocus
                  aria-label="Новое название доски"
                  className="rename-input"
                  value={renameTitle}
                  onChange={(e) => setRenameTitle(e.target.value)}
                  onKeyDown={(e) => {
                    // Enter при наборе раскладкой IME подтверждает ввод, а не название
                    if (e.nativeEvent.isComposing || e.keyCode === 229) {
                      e.preventDefault()
                      return
                    }
                    if (e.key === 'Enter') void renameBoard(b.id)
                    if (e.key === 'Escape') setRenaming(null)
                  }}
                />
                <button type="button" className="btn" onClick={() => void renameBoard(b.id)}>ОК</button>
                <button type="button" className="btn ghost" onClick={() => setRenaming(null)}>Отмена</button>
              </>
            ) : (
              <>
                <Link to={`/board/${b.id}`} className="title">{b.title}</Link>
                <div className="board-card-actions">
                  <span className="role-badge">owner</span>
                  <button
                    type="button"
                    className="btn ghost"
                    title="Переименовать"
                    aria-label={`Переименовать доску «${b.title}»`}
                    onClick={() => {
                      setRenaming(b.id)
                      setRenameTitle(b.title)
                    }}
                  >
                    ✎
                  </button>
                  <button
                    type="button"
                    className="btn ghost"
                    title="Удалить доску"
                    aria-label={`Удалить доску «${b.title}»`}
                    onClick={() => setPendingDelete({ id: b.id, title: b.title })}
                  >
                    🗑
                  </button>
                </div>
              </>
            )}
          </div>
        ))}
        {data && data.own.length === 0 && (
          <div className="empty-state">
            <div className="empty-ico">📋</div>
            <p className="hint">Пока нет ни одной доски — создайте первую кнопкой «Создать».</p>
          </div>
        )}
        </div>
      </div>

      <div className="boards-section">
        <h2>Доступные мне</h2>
        <div className="boards-grid">
        {(data?.shared ?? []).map((b) => (
          <div key={b.id} className="board-card">
            <Link to={`/board/${b.id}`} className="title">{b.title}</Link>
            <span className="role-badge">{b.role}</span>
          </div>
        ))}
        {data && data.shared.length === 0 && (
          <div className="empty-state">
            <div className="empty-ico">🤝</div>
            <p className="hint">Вам пока не дали доступ к чужим доскам. Попросите владельца поделиться.</p>
          </div>
        )}
        </div>
      </div>

      {pendingDelete && (
        <ConfirmDialog
          title="Удалить доску?"
          message={`Доска «${pendingDelete.title}» будет удалена безвозвратно вместе со всеми тикетами.`}
          confirmLabel="Удалить"
          onConfirm={() => { void removeBoard(pendingDelete.id) }}
          onClose={() => setPendingDelete(null)}
        />
      )}
    </div>
  )
}
