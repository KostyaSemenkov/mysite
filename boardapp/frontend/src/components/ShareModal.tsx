import { useEffect, useRef, useState } from 'react'
import { api, apiError } from '../api'

interface MemberRow {
  user: { id: string; username: string }
  role: string
}

/**
 * Доступ к доске — настоящий модальный <dialog>: фокус запирается внутри,
 * Esc и клик по фону закрывают (closedby="any"), после закрытия фокус
 * возвращается на кнопку «Поделиться».
 *
 * О закрытии сообщаем родителю из каждого пути отдельно (cancel, клик по фону,
 * кнопка): браузер не гарантирует событие close для закрытия по запросу —
 * без этого окно нельзя было бы открыть второй раз.
 */
export default function ShareModal({ boardId, onClose }: { boardId: string; onClose: () => void }) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const [members, setMembers] = useState<MemberRow[]>([])
  const [username, setUsername] = useState('')
  const [role, setRole] = useState<'editor' | 'viewer'>('editor')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [hints, setHints] = useState<string[]>([])

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (!dialog.open) dialog.showModal()
    // клик по фону: ловим в capture-фазе на document. Браузер с closedby="any"
    // закрывает окно до всплытия click, и тогда событие досталось бы канвасу
    // под окном, а родитель не узнал бы о закрытии; старый браузер закроем сами.
    const onPointerDown = (e: PointerEvent) => { if (e.target === dialog) close() }
    document.addEventListener('pointerdown', onPointerDown, true)
    return () => document.removeEventListener('pointerdown', onPointerDown, true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function load() {
    try {
      const { data } = await api.get(`/api/boards/${boardId}`)
      setMembers(data.members)
    } catch (err) {
      setError(apiError(err))
    }
  }

  useEffect(() => {
    load()
  }, [boardId])

  // подсказки имён по первым символам (>= 2) — в выпадающем списке поля
  useEffect(() => {
    const q = username.trim()
    if (q.length < 2) {
      setHints([])
      return
    }
    let alive = true
    const t = setTimeout(async () => {
      try {
        const { data } = await api.get('/api/users/search', { params: { q } })
        if (alive) setHints((data.items ?? []).map((u: { username: string }) => u.username))
      } catch {
        /* подсказки не критичны */
      }
    }, 250)
    return () => {
      alive = false
      clearTimeout(t)
    }
  }, [username])

  async function invite() {
    if (!username.trim()) return
    setBusy(true)
    setError('')
    try {
      await api.post(`/api/boards/${boardId}/members`, {
        username: username.trim(),
        role,
      })
      setUsername('')
      setHints([])
      await load()
    } catch (err) {
      setError(apiError(err))
    } finally {
      setBusy(false)
    }
  }

  async function kick(userId: string) {
    try {
      await api.delete(`/api/boards/${boardId}/members/${userId}`)
      await load()
    } catch (err) {
      setError(apiError(err))
    }
  }

  function close() {
    dialogRef.current?.close()
    onClose()
  }

  return (
    <dialog
      ref={dialogRef}
      className="share-dialog"
      aria-labelledby="share-title"
      closedby="any"
      onCancel={onClose}
      onClose={onClose}
    >
      <form className="share-panel" onSubmit={(e) => { e.preventDefault(); void invite() }}>
        <div className="share-head">
          <h2 id="share-title">Доступ к доске</h2>
          <button type="button" className="btn ghost" aria-label="Закрыть" onClick={close}>×</button>
        </div>

        <label htmlFor="share-username">Кого пригласить</label>
        <input
          id="share-username"
          name="username"
          list="user-hints"
          autoComplete="off"
          placeholder="Начните вводить имя…"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <datalist id="user-hints">
          {hints.map((h) => <option key={h} value={h} />)}
        </datalist>

        <label htmlFor="share-role">Права</label>
        <div className="share-invite">
          <select id="share-role" name="role" value={role}
                  onChange={(e) => setRole(e.target.value as 'editor' | 'viewer')}>
            <option value="editor">редактор — может менять доску</option>
            <option value="viewer">наблюдатель — только смотрит</option>
          </select>
          <button type="submit" className="btn" disabled={busy || !username.trim()}>
            {busy ? 'Добавляем…' : 'Пригласить'}
          </button>
        </div>
        {error && <div className="error" role="alert">{error}</div>}

        <ul className="share-members" aria-label="Участники доски">
          {members.length === 0 && <li className="hint">Участников пока нет.</li>}
          {members.map((m) => (
            <li key={m.user.id}>
              <span className="share-member-name">{m.user.username}</span>
              <span className="role-badge">{m.role}</span>
              <button type="button" className="btn ghost" aria-label={`Убрать ${m.user.username}`}
                      onClick={() => kick(m.user.id)}>Убрать</button>
            </li>
          ))}
        </ul>
      </form>
    </dialog>
  )
}
