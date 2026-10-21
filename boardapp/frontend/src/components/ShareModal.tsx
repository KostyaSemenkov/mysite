import { useEffect, useState } from 'react'
import { api, apiError } from '../api'

interface MemberRow {
  user: { id: string; username: string }
  role: string
}

export default function ShareModal({ boardId, onClose }: { boardId: string; onClose: () => void }) {
  const [members, setMembers] = useState<MemberRow[]>([])
  const [username, setUsername] = useState('')
  const [role, setRole] = useState<'editor' | 'viewer'>('editor')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [hints, setHints] = useState<string[]>([])

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

  // подсказки имён по первым символам (>= 2)
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

  return (
    <dialog open onClick={(e) => e.target === e.currentTarget && onClose()} style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,.55)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100,
    }}>
      <div onClick={(e) => e.stopPropagation()} style={{
        width: 420, background: 'var(--panel)', border: '1px solid var(--border)',
        borderRadius: 12, padding: 22,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 14 }}>
          <h3 style={{ margin: 0 }}>Доступ к доске</h3>
          <button className="btn ghost" onClick={onClose}>×</button>
        </div>

        <div style={{ display: 'flex', gap: 8, position: 'relative' }}>
          <input
            placeholder="Начните вводить имя…"
            list="user-hints"
            autoComplete="off"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            style={{ flex: 1, background: 'var(--panel2)', border: '1px solid var(--border)', borderRadius: 8, padding: '8px 10px', color: 'var(--text)' }}
          />
          <datalist id="user-hints">
            {hints.map((h) => <option key={h} value={h} />)}
          </datalist>
          {hints.length > 0 && username.trim().length >= 2 && (
            <div style={{
              position: 'absolute', top: '100%', left: 0, width: '60%', zIndex: 50,
              background: 'var(--panel2)', border: '1px solid var(--border)',
              borderRadius: 8, marginTop: 4, overflow: 'hidden',
            }}>
              {hints.map((h) => (
                <div
                  key={h}
                  onClick={() => { setUsername(h); setHints([]) }}
                  style={{ padding: '7px 10px', cursor: 'pointer', fontSize: 14 }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--border)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  {h}
                </div>
              ))}
            </div>
          )}
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as 'editor' | 'viewer')}
            style={{ background: 'var(--panel2)', border: '1px solid var(--border)', borderRadius: 8, padding: '8px', color: 'var(--text)' }}
          >
            <option value="editor">редактор</option>
            <option value="viewer">наблюдатель</option>
          </select>
          <button className="btn" onClick={invite} disabled={busy}>Пригласить</button>
        </div>
        {error && <div className="error" style={{ marginTop: 8 }}>{error}</div>}

        <div style={{ marginTop: 16 }}>
          {members.length === 0 && <p className="hint">Участников пока нет.</p>}
          {members.map((m) => (
            <div key={m.user.id} style={{
              display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px',
              background: 'var(--panel2)', borderRadius: 8, marginTop: 6,
            }}>
              <span style={{ flex: 1 }}>{m.user.username}</span>
              <span className="role-badge">{m.role}</span>
              <button className="btn ghost" onClick={() => kick(m.user.id)}>Убрать</button>
            </div>
          ))}
        </div>
      </div>
    </dialog>
  )
}
