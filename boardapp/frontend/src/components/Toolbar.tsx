import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useBoard } from '../store'
import { onStatus, type WsStatus } from '../ws'

const STATUS_LABEL: Record<WsStatus, string> = {
  connecting: 'подключение…',
  online: 'онлайн',
  reconnecting: 'переподключение…',
}

export default function Toolbar({ onExport }: { onExport: () => void }) {
  const title = useBoard((s) => s.boardTitle)
  const role = useBoard((s) => s.role)
  const presence = useBoard((s) => s.presence)
  const canUndo = useBoard((s) => s.undoStack.length > 0)
  const canRedo = useBoard((s) => s.redoStack.length > 0)
  const undo = useBoard((s) => s.undo)
  const redo = useBoard((s) => s.redo)
  const [status, setStatus] = useState<WsStatus>('connecting')

  useEffect(() => onStatus(setStatus), [])

  return (
    <div className="toolbar">
      <Link to="/" style={{ color: 'var(--muted)' }}>← Доски</Link>
      <strong style={{ maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {title}
      </strong>
      {role === 'viewer' && <span className="role-badge">только просмотр</span>}
      <div className="sep" />
      <button className="btn ghost" onClick={undo} disabled={!canUndo} title="Ctrl+Z">
        ↶ Отменить
      </button>
      <button className="btn ghost" onClick={redo} disabled={!canRedo} title="Ctrl+Shift+Z">
        ↷ Вернуть
      </button>
      <div className="sep" />
      <button className="btn ghost" onClick={onExport}>
        Скачать PNG
      </button>
      <div className="sep" />
      <div className="ws-status">
        <span className={`ws-dot ${status === 'online' ? 'online' : status === 'reconnecting' ? 'reconnecting' : ''}`} />
        {STATUS_LABEL[status]}
      </div>
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
