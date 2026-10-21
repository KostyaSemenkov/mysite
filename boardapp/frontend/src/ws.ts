import { getToken } from './api'
import { useBoard } from './store'
import {
  applyEdgeCreated, applyEdgeDeleted, applyInit, applyTicketCreated,
  applyTicketDeleted, applyTicketUpdated, applyZoneCreated, applyZoneDeleted,
  applyZoneUpdated,
} from './store'

export type WsStatus = 'connecting' | 'online' | 'reconnecting'

type StatusListener = (s: WsStatus) => void
const statusListeners = new Set<StatusListener>()

export function onStatus(fn: StatusListener): () => void {
  statusListeners.add(fn)
  fn(currentStatus)
  return () => statusListeners.delete(fn)
}

let currentStatus: WsStatus = 'connecting'
function setStatus(s: WsStatus) {
  currentStatus = s
  statusListeners.forEach((fn) => fn(s))
}

let ws: WebSocket | null = null
let boardId: string | null = null
let closedByUs = false
let retryDelay = 500
let myUserId: string | null = null

export function setMyUserId(id: string) {
  myUserId = id
}

export function connectBoard(id: string) {
  if (boardId === id && ws && ws.readyState <= WebSocket.OPEN) return
  disconnect()
  boardId = id
  closedByUs = false
  open()
}

function open() {
  if (!boardId) return
  setStatus('connecting')
  const token = getToken() ?? ''
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  ws = new WebSocket(`${proto}://${location.host}/boards/ws/boards/${boardId}?token=${token}`)

  ws.onopen = () => {
    retryDelay = 500
    setStatus('online')
  }

  ws.onmessage = (ev) => {
    let msg: any
    try {
      msg = JSON.parse(ev.data)
    } catch {
      return
    }
    if (msg.actor && myUserId && msg.actor === myUserId) return // подавление эха
    const s = useBoard.getState()
    switch (msg.type) {
      case 'init':
        applyInit(msg.data)
        break
      case 'ticket:created':
        applyTicketCreated(msg.data)
        break
      case 'ticket:updated':
        applyTicketUpdated(msg.data.id, msg.data.patch)
        break
      case 'ticket:deleted':
        applyTicketDeleted(msg.data.id)
        break
      case 'edge:created':
        applyEdgeCreated(msg.data)
        break
      case 'edge:deleted':
        applyEdgeDeleted(msg.data.id)
        break
      case 'zone:created':
        applyZoneCreated(msg.data)
        break
      case 'zone:updated':
        applyZoneUpdated(msg.data.id, msg.data.patch)
        break
      case 'zone:deleted':
        applyZoneDeleted(msg.data.id)
        break
      case 'presence:join':
        s.presenceJoin(msg.data)
        break
      case 'presence:leave':
        s.presenceLeave(msg.data.userId)
        break
      case 'cursor':
        s.updateCursor(msg.data.userId, msg.data.x, msg.data.y)
        break
      case 'error':
        console.warn('WS error:', msg.data?.message)
        break
    }
  }

  ws.onclose = () => {
    if (closedByUs || !boardId) return
    setStatus('reconnecting')
    setTimeout(() => {
      if (!closedByUs && boardId) open()
    }, retryDelay)
    retryDelay = Math.min(retryDelay * 2, 8000)
  }

  ws.onerror = () => ws?.close()
}

export function disconnect() {
  closedByUs = true
  boardId = null
  ws?.close()
  ws = null
  setStatus('connecting')
}

export function send(msg: unknown) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(msg))
  } else {
    console.warn('WS не подключён, сообщение отброшено', msg)
  }
}

// троттлинг курсора ~50 мс
let lastCursorSent = 0
export function sendCursorThrottled(x: number, y: number) {
  const now = performance.now()
  if (now - lastCursorSent < 50) return
  lastCursorSent = now
  send({ type: 'cursor:move', data: { x, y } })
}
