import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useBoard } from '../store'
import { onStatus, type WsStatus } from '../ws'

const STATUS_LABEL: Record<WsStatus, string> = {
  connecting: 'подключение…',
  online: 'онлайн',
  saving: 'сохранение…',
  reconnecting: 'переподключение…',
}

export default function Toolbar({ onExport }: { onExport: () => void }) {
  const title = useBoard((s) => s.boardTitle)
  const role = useBoard((s) => s.role)
  const syncError = useBoard((s) => s.syncError)
  const presence = useBoard((s) => s.presence)
  const canUndo = useBoard((s) => s.undoStack.length > 0)
  const canRedo = useBoard((s) => s.redoStack.length > 0)
  const undo = useBoard((s) => s.undo)
  const redo = useBoard((s) => s.redo)
  const [status, setStatus] = useState<WsStatus>('connecting')
  // экранный диктор слышит только потерю и восстановление связи, а не каждое сохранение
  const [announce, setAnnounce] = useState('')
  const previous = useRef<WsStatus>(status)

  useEffect(() => onStatus((next) => {
    if (next === 'reconnecting') {
      setAnnounce('Связь с доской потеряна — переподключаемся. Изменения сохранятся в очереди.')
    } else if (next === 'online' && previous.current === 'reconnecting') {
      setAnnounce('Связь восстановлена.')
    }
    previous.current = next
    setStatus(next)
  }), [])

  return (
    <div className="toolbar" role="toolbar" aria-label="Действия с доской">
      <Link to="/" style={{ color: 'var(--muted)' }}>← Доски</Link>
      <a href="/" title="На главную сайта" aria-label="На главную сайта"
         style={{ fontSize: 18, textDecoration: 'none' }}>🏠</a>
      <strong style={{ maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {title}
      </strong>
      {role === 'viewer' && <span className="role-badge">только просмотр</span>}
      <div className="sep" aria-hidden="true" />
      <button type="button" className="btn ghost" onClick={undo} disabled={!canUndo}
              title="Ctrl+Z" aria-keyshortcuts="Control+Z">
        ↶ Отменить
      </button>
      <button type="button" className="btn ghost" onClick={redo} disabled={!canRedo}
              title="Ctrl+Shift+Z" aria-keyshortcuts="Control+Shift+Z">
        ↷ Вернуть
      </button>
      <div className="sep" aria-hidden="true" />
      <button type="button" className="btn ghost" onClick={onExport}>Скачать PNG</button>
      <div className="sep" aria-hidden="true" />
      <div className="ws-status">
        <span className={`ws-dot ${status === 'online' ? 'online' : status === 'reconnecting' ? 'reconnecting' : ''}`} />
        {STATUS_LABEL[status]}
      </div>
      <span className="visually-hidden" role="status" aria-live="polite">{announce}</span>
      {syncError && <span className="role-badge" role="alert">{syncError}</span>}
      <div className="presence-list">
        {presence.map((p) => (
          <span key={p.userId} className="presence-chip" style={{ ['--presence-color' as string]: p.color }}>
            {p.username}
          </span>
        ))}
      </div>
    </div>
  )
}
