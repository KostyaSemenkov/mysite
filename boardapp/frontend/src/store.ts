import { create } from 'zustand'
import type { Connection } from '@xyflow/react'
import { send } from './ws'
import {
  EV, edgeMsgToEdge, emit, ticketToNode, zoneToNode,
  type BoardChange, type BoardEvent, type BoardInitMsg, type BoardMutation,
  type EdgeMsg, type Presence, type TicketMsg, type ZoneMsg,
} from './boardEvents'

export interface TicketData extends Record<string, unknown> {
  text: string
  color: string
  zoneId: string | null
  editing?: boolean
}

export interface UndoEntry {
  undo: () => void
  redo: () => void
}

export const STICKER_COLORS = ['#FFF3B1', '#FFD6A5', '#CAFFBF', '#9BF6FF', '#BDB2FF', '#FFC6FF']

// плотные цвета зон — отличны от ярких стикеров
export const ZONE_COLORS = ['#7a4a2b', '#5a5a2f', '#5d3a52']

interface Cursor {
  userId: string
  x: number
  y: number
  color: string
}

interface BoardState {
  boardTitle: string
  role: string
  syncError: string
  presence: Presence[]
  cursors: Cursor[]
  undoStack: UndoEntry[]
  redoStack: UndoEntry[]
  reset: () => void
  presenceJoin: (data: Presence) => void
  presenceLeave: (userId: string) => void
  updateCursor: (userId: string, x: number, y: number) => void
  pushUndo: (entry: UndoEntry) => void
  undo: () => void
  redo: () => void
}

export const useBoard = create<BoardState>((set, get) => ({
  boardTitle: '',
  role: 'viewer',
  syncError: '',
  presence: [],
  cursors: [],
  undoStack: [],
  redoStack: [],

  reset: () => set({ boardTitle: '', role: 'viewer', syncError: '', presence: [], cursors: [],
                     undoStack: [], redoStack: [] }),

  presenceJoin: (p) =>
    set((s) => ({
      presence: s.presence.some((x) => x.userId === p.userId)
        ? s.presence.map((x) => (x.userId === p.userId ? p : x))
        : [...s.presence, p],
    })),

  presenceLeave: (userId) =>
    set((s) => ({
      presence: s.presence.filter((p) => p.userId !== userId),
      cursors: s.cursors.filter((c) => c.userId !== userId),
    })),

  updateCursor: (userId, x, y) =>
    set((s) => {
      const p = s.presence.find((pr) => pr.userId === userId)
      if (!p) return s
      const exists = s.cursors.some((c) => c.userId === userId)
      return {
        cursors: exists
          ? s.cursors.map((c) => (c.userId === userId ? { ...c, x, y } : c))
          : [...s.cursors, { userId, x, y, color: p.color }],
      }
    }),

  pushUndo: (entry) =>
    set((s) => ({
      undoStack: [...s.undoStack.slice(-99), entry],
      redoStack: [],
    })),

  undo: () => {
    const stack = get().undoStack
    const entry = stack[stack.length - 1]
    if (!entry) return
    entry.undo()
    set({ undoStack: stack.slice(0, -1), redoStack: [...get().redoStack, entry] })
  },

  redo: () => {
    const stack = get().redoStack
    const entry = stack[stack.length - 1]
    if (!entry) return
    entry.redo()
    set({ redoStack: stack.slice(0, -1), undoStack: [...get().undoStack, entry] })
  },
}))

// --- применение изменений к канве (события слушает редактор) ---

/** Авторост высоты тикета под текст; синхронизировано с бэкендом (_ticket_height).
 *  Под крупный шрифт 24px: ~13 знаков/строку, 32px на строку,
 *  база 56px (паддинги + резерв под точки цветов и счётчик), потолок 760px. */
export function ticketAutoHeight(text: string): number {
  let lines = 0
  for (const ln of text.split('\n')) {
    lines += Math.max(1, Math.ceil(ln.length / 13))
  }
  return Math.min(760, Math.max(130, 56 + lines * 32))
}

export function applyInit(data: BoardInitMsg) {
  useBoard.setState({
    boardTitle: data.board.title, role: data.role, presence: data.presence, cursors: [],
  })
  emit(EV.init, {
    nodes: [
      ...(data.zones ?? []).map(zoneToNode),
      ...data.tickets.map(ticketToNode),
    ],
    edges: data.edges.map(edgeMsgToEdge),
  })
}

export function applyTicketCreated(t: TicketMsg) {
  emit(EV.ticketCreated, ticketToNode(t))
}

export function applyTicketUpdated(id: string, patch: Partial<TicketMsg> & { editing?: boolean }) {
  emit(EV.ticketUpdated, { id, patch })
}

export function applyTicketDeleted(id: string) {
  emit(EV.ticketDeleted, { id })
}

export function applyEdgeCreated(e: EdgeMsg) {
  emit(EV.edgeCreated, edgeMsgToEdge(e))
}

function applyEdgeUpdated(id: string, label: string) {
  emit(EV.edgeUpdated, { id, label })
}

export function applyEdgeDeleted(id: string) {
  emit(EV.edgeDeleted, { id })
}

export function applyZoneCreated(z: ZoneMsg) {
  emit(EV.zoneCreated, zoneToNode(z))
}

export function applyZoneUpdated(id: string, patch: Partial<ZoneMsg>) {
  emit(EV.zoneUpdated, { id, patch })
}

export function applyZoneDeleted(id: string) {
  emit(EV.zoneDeleted, { id })
}

export function applyBoardEvent(event: BoardEvent) {
  switch (event.type) {
    case 'ticket:created': applyTicketCreated(event.data); break
    case 'ticket:updated': applyTicketUpdated(event.data.id, event.data.patch); break
    case 'ticket:deleted': applyTicketDeleted(event.data.id); break
    case 'edge:created': applyEdgeCreated(event.data); break
    case 'edge:updated': applyEdgeUpdated(event.data.id, event.data.label); break
    case 'edge:deleted': applyEdgeDeleted(event.data.id); break
    case 'zone:created': applyZoneCreated(event.data); break
    case 'zone:updated': applyZoneUpdated(event.data.id, event.data.patch); break
    case 'zone:deleted': applyZoneDeleted(event.data.id); break
  }
}

export function applyPendingMutation(mutation: BoardMutation) {
  if (mutation.type === 'board:batch') {
    mutation.data.changes.forEach(applyPendingMutation)
    return
  }
  switch (mutation.type) {
    case 'ticket:create': applyTicketCreated(mutation.data); break
    case 'ticket:update': applyTicketUpdated(mutation.data.id, mutation.data.patch); break
    case 'ticket:delete': applyTicketDeleted(mutation.data.id); break
    case 'edge:create': applyEdgeCreated(mutation.data); break
    case 'edge:update': applyEdgeUpdated(mutation.data.id, mutation.data.label); break
    case 'edge:delete': applyEdgeDeleted(mutation.data.id); break
    case 'zone:create': applyZoneCreated(mutation.data); break
    case 'zone:update': applyZoneUpdated(mutation.data.id, mutation.data.patch); break
    case 'zone:delete': applyZoneDeleted(mutation.data.id); break
  }
}

export function commitBatch(changes: BoardChange[], inverse: BoardChange[]) {
  if (changes.length === 0) return
  const apply = (batch: BoardChange[]) => {
    const mutation = { type: 'board:batch', data: { changes: batch } } as const
    send(mutation)
    applyPendingMutation(mutation)
  }
  apply(changes)
  useBoard.getState().pushUndo({ undo: () => apply(inverse), redo: () => apply(changes) })
}

/** Запрос на удаление ноды (тикет/группа) — редактор найдёт снимок и удалит. */
export function requestDeleteNode(id: string) {
  emit(EV.nodeDeleteRequest, { id })
}

// --- операции: локально (событием) + на сервер ---

export function createTicket(x: number, y: number, color = STICKER_COLORS[0], zoneId: string | null = null) {
  const id = crypto.randomUUID()
  const msg: TicketMsg = { id, x, y, width: 200, height: 130, text: '', color, zoneId }
  send({ type: 'ticket:create', data: msg })
  applyTicketCreated(msg)
  // новый тикет сразу в режиме редактирования
  applyTicketUpdated(id, { editing: true })
  useBoard.getState().pushUndo({
    undo: () => {
      send({ type: 'ticket:delete', data: { id } })
      applyTicketDeleted(id)
    },
    redo: () => {
      send({ type: 'ticket:create', data: msg })
      applyTicketCreated(msg)
    },
  })
  return id
}

export function updateTicket(id: string, patch: Partial<TicketMsg> & { editing?: boolean },
                             undoPatch?: Partial<TicketMsg>) {
  const toServer: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(patch)) {
    if (k !== 'editing') toServer[k] = v
  }
  if (typeof toServer.text === 'string') {
    toServer.text = (toServer.text as string).slice(0, 100) // жёсткий лимит тикета
  }
  if (Object.keys(toServer).length > 0) {
    send({ type: 'ticket:update', data: { id, patch: toServer } })
  }
  const clamped = { ...patch }
  if (typeof clamped.text === 'string') {
    clamped.text = clamped.text.slice(0, 100)
  }
  applyTicketUpdated(id, clamped)
  if (undoPatch) {
    useBoard.getState().pushUndo({
      undo: () => {
        send({ type: 'ticket:update', data: { id, patch: undoPatch } })
        applyTicketUpdated(id, undoPatch)
      },
      redo: () => {
        send({ type: 'ticket:update', data: { id, patch: toServer as Partial<TicketMsg> } })
        applyTicketUpdated(id, toServer as Partial<TicketMsg>)
      },
    })
  }
}

export function createEdge(connection: Connection) {
  if (!connection.source || !connection.target || connection.source === connection.target) return
  const id = crypto.randomUUID()
  const msg: EdgeMsg = { id, source: connection.source, target: connection.target }
  send({ type: 'edge:create', data: msg })
  applyEdgeCreated(msg)
  useBoard.getState().pushUndo({
    undo: () => {
      send({ type: 'edge:delete', data: { id } })
      applyEdgeDeleted(id)
    },
    redo: () => {
      send({ type: 'edge:create', data: msg })
      applyEdgeCreated(msg)
    },
  })
}

// --- зоны ---

export function createZone(x: number, y: number, title = '', color = ZONE_COLORS[0]) {
  const id = crypto.randomUUID()
  const msg: ZoneMsg = { id, title, color, x, y, width: 420, height: 280 }
  send({ type: 'zone:create', data: msg })
  applyZoneCreated(msg)
  useBoard.getState().pushUndo({
    undo: () => {
      send({ type: 'zone:delete', data: { id } })
      applyZoneDeleted(id)
    },
    redo: () => {
      send({ type: 'zone:create', data: msg })
      applyZoneCreated(msg)
    },
  })
  return id
}

export function updateZone(id: string, patch: Partial<ZoneMsg>, undoPatch?: Partial<ZoneMsg>) {
  send({ type: 'zone:update', data: { id, patch } })
  applyZoneUpdated(id, patch)
  if (undoPatch) {
    useBoard.getState().pushUndo({
      undo: () => {
        send({ type: 'zone:update', data: { id, patch: undoPatch } })
        applyZoneUpdated(id, undoPatch)
      },
      redo: () => {
        send({ type: 'zone:update', data: { id, patch } })
        applyZoneUpdated(id, patch)
      },
    })
  }
}
