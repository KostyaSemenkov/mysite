import { getToken } from './api'
import type { BoardEvent, BoardInitMsg, BoardMutation, Presence } from './boardEvents'
import { applyBoardEvent, applyInit, applyPendingMutation, useBoard } from './store'

export type WsStatus = 'connecting' | 'online' | 'saving' | 'reconnecting'

type Operation = { clientId: string; sequence: number }
type Pending = { sequence: number; mutation: BoardMutation }
type ServerMessage = (BoardEvent
  | { type: 'init'; data: BoardInitMsg }
  | { type: 'board:batch'; data: { events: BoardEvent[] } }
  | { type: 'op:ack' }
  | { type: 'presence:join'; data: Presence }
  | { type: 'presence:leave'; data: { userId: string } }
  | { type: 'cursor'; data: { userId: string; x: number; y: number } }
  | { type: 'error'; data: { message: string } }
) & { operation?: Operation; actor?: string }

interface Channel {
  boardId: string
  token: string
  clientId: string
  sequence: number
  pending: Pending[]
  socket: WebSocket | null
  ready: boolean
  retryDelay: number
  retryTimer?: number
  ackTimer?: number
  error: string
}

const channels = new Map<string, Channel>()
let active: Channel | undefined
let myUserId: string | null = null
let currentStatus: WsStatus = 'connecting'
const statusListeners = new Set<(status: WsStatus) => void>()

export function onStatus(fn: (status: WsStatus) => void): () => void {
  statusListeners.add(fn)
  fn(currentStatus)
  return () => { statusListeners.delete(fn) }
}

function setStatus(status: WsStatus) {
  currentStatus = status
  statusListeners.forEach((fn) => fn(status))
}

export function setMyUserId(id: string) {
  myUserId = id
}

export function connectBoard(boardId: string) {
  if (active?.boardId === boardId) return
  disconnect()
  const token = getToken() ?? ''
  let channel = channels.get(boardId)
  if (channel && channel.token !== token) {
    stop(channel)
    channel = undefined
  }
  if (!channel) {
    channel = {
      boardId, token, clientId: crypto.randomUUID(), sequence: 0, pending: [],
      socket: null, ready: false, retryDelay: 500, error: '',
    }
    channels.set(boardId, channel)
  }
  active = channel
  useBoard.setState({ syncError: channel.error })
  setStatus('connecting')
  // A background connection has not been updating the displayed board.
  closeSocket(channel)
  open(channel)
}

function closeSocket(channel: Channel) {
  window.clearTimeout(channel.retryTimer)
  window.clearTimeout(channel.ackTimer)
  channel.retryTimer = undefined
  channel.ackTimer = undefined
  channel.ready = false
  const socket = channel.socket
  channel.socket = null
  socket?.close()
}

function stop(channel: Channel) {
  closeSocket(channel)
  if (channels.get(channel.boardId) === channel) channels.delete(channel.boardId)
}

export function disconnect() {
  const previous = active
  active = undefined
  if (previous && previous.pending.length === 0 && !previous.error) stop(previous)
  else if (previous && previous.pending.length === 0) closeSocket(previous)
}

function pump(channel: Channel) {
  const socket = channel.socket
  if (!channel.ready || socket?.readyState !== WebSocket.OPEN) return
  const next = channel.pending[0]
  if (channel === active) setStatus(next ? 'saving' : 'online')
  if (!next) {
    if (channel !== active) {
      if (channel.error) closeSocket(channel)
      else stop(channel)
    }
    return
  }
  if (channel.ackTimer !== undefined) return
  socket.send(JSON.stringify({
    ...next.mutation, operation: { clientId: channel.clientId, sequence: next.sequence },
  }))
  // Keep the operation queued until a committed response arrives.
  channel.ackTimer = window.setTimeout(() => socket.close(), 8000)
}

function open(channel: Channel) {
  if ((getToken() ?? '') !== channel.token) {
    stop(channel)
    return
  }
  channel.retryTimer = undefined
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
  const params = new URLSearchParams({ token: channel.token, clientId: channel.clientId })
  const socket = new WebSocket(`${protocol}://${location.host}/boards/ws/boards/${channel.boardId}?${params}`)
  channel.socket = socket

  socket.onmessage = (ev) => {
    if (channel.socket !== socket) return
    let msg: ServerMessage
    try {
      msg = JSON.parse(ev.data)
    } catch {
      return
    }

    if (msg.type === 'init') {
      channel.ready = true
      channel.retryDelay = 500
      const lastSequence = msg.data.lastSequence ?? 0
      channel.pending = channel.pending.filter(({ sequence }) => sequence > lastSequence)
      if (channel === active) {
        applyInit(msg.data)
        channel.pending.forEach(({ mutation }) => applyPendingMutation(mutation))
      }
      pump(channel)
      return
    }
    if (!channel.ready) return

    const confirmed = msg.operation?.clientId === channel.clientId
      && msg.operation.sequence === channel.pending[0]?.sequence
    if (confirmed) {
      channel.pending.shift()
      window.clearTimeout(channel.ackTimer)
      channel.ackTimer = undefined
    }

    if (msg.type === 'error') {
      channel.error = msg.data.message
      if (channel === active) {
        useBoard.setState({ syncError: channel.error, undoStack: [], redoStack: [] })
      }
      // Reload the authoritative snapshot before continuing after a rejected edit.
      socket.close()
      return
    }

    if (channel === active) {
      const state = useBoard.getState()
      switch (msg.type) {
        case 'presence:join': state.presenceJoin(msg.data); return
        case 'presence:leave': state.presenceLeave(msg.data.userId); return
        case 'cursor':
          if (msg.actor !== myUserId) state.updateCursor(msg.data.userId, msg.data.x, msg.data.y)
          return
        case 'op:ack':
          socket.close()
          return
        case 'board:batch': msg.data.events.forEach(applyBoardEvent); break
        default: applyBoardEvent(msg)
      }
      channel.pending.forEach(({ mutation }) => applyPendingMutation(mutation))
    }
    if (confirmed) pump(channel)
  }

  socket.onclose = () => {
    if (channel.socket !== socket) return
    closeSocket(channel)
    if (channel !== active && channel.pending.length === 0) {
      if (!channel.error) stop(channel)
      return
    }
    if (channel === active) setStatus('reconnecting')
    channel.retryTimer = window.setTimeout(() => open(channel), channel.retryDelay)
    channel.retryDelay = Math.min(channel.retryDelay * 2, 8000)
  }
  socket.onerror = () => socket.close()
}

export function send(mutation: BoardMutation) {
  if (!active) return
  active.pending.push({ sequence: ++active.sequence, mutation })
  pump(active)
}

let lastCursorSent = 0
export function sendCursorThrottled(x: number, y: number) {
  const socket = active?.socket
  if (!active?.ready || socket?.readyState !== WebSocket.OPEN) return
  const now = performance.now()
  if (now - lastCursorSent < 50) return
  lastCursorSent = now
  socket.send(JSON.stringify({ type: 'cursor:move', data: { x, y } }))
}
