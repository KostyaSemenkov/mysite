import { create } from 'zustand'
import type { Connection } from '@xyflow/react'
import { send } from './ws'
import {
  EV, edgeMsgToEdge, emit, ticketToNode, zoneToNode,
  type EdgeMsg, type TicketMsg, type ZoneMsg,
} from './boardEvents'

export interface TicketData extends Record<string, unknown> {
  text: string
  color: string
  editing?: boolean
}

export interface UndoEntry {
  undo: () => void
  redo: () => void
}

export const STICKER_COLORS = ['#FFF3B1', '#FFD6A5', '#CAFFBF', '#9BF6FF', '#BDB2FF', '#FFC6FF']

// плотные цвета зон — отличны от ярких стикеров
export const ZONE_COLORS = ['#7a4a2b', '#5a5a2f', '#5d3a52']

interface Presence {
  userId: string
  username: string
  color: string
}

interface Cursor {
  userId: string
  x: number
  y: number
  color: string
}

interface BoardState {
  boardTitle: string
  role: string
  presence: Presence[]
  cursors: Cursor[]
  undoStack: UndoEntry[]
  redoStack: UndoEntry[]
  setTitle: (title: string) => void
  setRole: (role: string) => void
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
  presence: [],
  cursors: [],
  undoStack: [],
  redoStack: [],

  setTitle: (boardTitle) => set({ boardTitle }),
  setRole: (role) => set({ role }),
  reset: () => set({ boardTitle: '', role: 'viewer', presence: [], cursors: [],
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
 *  Консервативные константы: 19 знаков/строку, 22px на строку,
 *  база 48px (паддинги + резерв под точки цветов и счётчик), потолок 720px. */
export function ticketAutoHeight(text: string): number {
  let lines = 0
  for (const ln of text.split('\n')) {
    lines += Math.max(1, Math.ceil(ln.length / 19))
  }
  return Math.min(720, Math.max(110, 48 + lines * 22))
}

export function applyInit(data: {
  board: { title: string }
  tickets: TicketMsg[]
  edges: EdgeMsg[]
  zones: ZoneMsg[]
  role: string
}) {
  useBoard.getState().setTitle(data.board.title)
  useBoard.getState().setRole(data.role)
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

export function applyTicketUpdated(id: string, patch: Partial<TicketMsg>) {
  emit(EV.ticketUpdated, { id, patch })
}

export function applyTicketDeleted(id: string) {
  emit(EV.ticketDeleted, { id })
}

export function applyEdgeCreated(e: EdgeMsg) {
  emit(EV.edgeCreated, edgeMsgToEdge(e))
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

// --- операции: локально (событием) + на сервер; эхо подавляется по actor в ws.ts ---

export function createTicket(x: number, y: number, color = STICKER_COLORS[0]) {
  const id = crypto.randomUUID()
  const msg: TicketMsg = { id, x, y, width: 200, height: 100, text: '', color }
  send({ type: 'ticket:create', data: msg })
  applyTicketCreated(msg)
  // новый тикет сразу в режиме редактирования
  applyTicketUpdated(id, { editing: true } as never)
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

// снять editing-флаг локально (после commit в TicketNode)
export function stopEditing(id: string) {
  emit(EV.ticketUpdated, { id, patch: { editing: false } as never })
}

export function deleteTicket(id: string) {
  // снимок для undo берём из DOM-события редактора: упрощённо — редактор
  // перед драгом/удалением сам держит данные; здесь только операции
  send({ type: 'ticket:delete', data: { id } })
  applyTicketDeleted(id)
}

export function deleteTicketWithSnapshot(node: {
  id: string; position: { x: number; y: number };
  width?: number; height?: number; data: TicketData;
}) {
  const msg: TicketMsg = {
    id: node.id, x: node.position.x, y: node.position.y,
    width: node.width ?? 200, height: node.height ?? 100,
    text: node.data.text, color: node.data.color,
  }
  send({ type: 'ticket:delete', data: { id: node.id } })
  applyTicketDeleted(node.id)
  useBoard.getState().pushUndo({
    undo: () => {
      send({ type: 'ticket:create', data: msg })
      applyTicketCreated(msg)
    },
    redo: () => {
      send({ type: 'ticket:delete', data: { id: node.id } })
      applyTicketDeleted(node.id)
    },
  })
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

export function deleteEdge(id: string) {
  send({ type: 'edge:delete', data: { id } })
  applyEdgeDeleted(id)
}

export function deleteEdgeWithSnapshot(edge: { id: string; source: string; target: string }) {
  const msg: EdgeMsg = { id: edge.id, source: edge.source, target: edge.target }
  send({ type: 'edge:delete', data: { id: edge.id } })
  applyEdgeDeleted(edge.id)
  useBoard.getState().pushUndo({
    undo: () => {
      send({ type: 'edge:create', data: msg })
      applyEdgeCreated(msg)
    },
    redo: () => {
      send({ type: 'edge:delete', data: { id: edge.id } })
      applyEdgeDeleted(edge.id)
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

export function deleteZoneWithSnapshot(node: {
  id: string; position: { x: number; y: number };
  width?: number; height?: number; data: { title: string };
}) {
  const msg: ZoneMsg = {
    id: node.id, title: node.data.title,
    x: node.position.x, y: node.position.y,
    width: node.width ?? 420, height: node.height ?? 280,
  }
  send({ type: 'zone:delete', data: { id: node.id } })
  applyZoneDeleted(node.id)
  useBoard.getState().pushUndo({
    undo: () => {
      send({ type: 'zone:create', data: msg })
      applyZoneCreated(msg)
    },
    redo: () => {
      send({ type: 'zone:delete', data: { id: node.id } })
      applyZoneDeleted(node.id)
    },
  })
}
