import { create } from 'zustand'
import type { Connection, Edge, NodeChange } from '@xyflow/react'
import { applyNodeChanges } from '@xyflow/react'
import { send } from './ws'

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
  boardId: string | null
  boardTitle: string
  role: string
  nodes: Node<TicketData>[]
  edges: Edge[]
  presence: Presence[]
  cursors: Cursor[]
  undoStack: UndoEntry[]
  redoStack: UndoEntry[]
  setBoard: (id: string | null, title?: string) => void
  initFromServer: (data: {
    board: { title: string }
    tickets: TicketMsg[]
    edges: EdgeMsg[]
    role: string
  }) => void
  applyNodeChangesLocally: (changes: NodeChange[]) => void
  setEdges: (updater: (eds: Edge[]) => Edge[]) => void
  remoteTicketCreated: (data: TicketMsg) => void
  remoteTicketUpdated: (id: string, patch: Partial<TicketMsg>) => void
  remoteTicketDeleted: (id: string) => void
  remoteEdgeCreated: (data: EdgeMsg) => void
  remoteEdgeDeleted: (id: string) => void
  presenceJoin: (data: Presence) => void
  presenceLeave: (userId: string) => void
  updateCursor: (userId: string, x: number, y: number) => void
  pushUndo: (entry: UndoEntry) => void
  undo: () => void
  redo: () => void
}

export interface TicketMsg {
  id: string
  x: number
  y: number
  width: number
  height: number
  text: string
  color: string
}

export interface EdgeMsg {
  id: string
  source: string
  target: string
}

import type { Node } from '@xyflow/react'

export const useBoard = create<BoardState>((set, get) => ({
  boardId: null,
  boardTitle: '',
  role: 'viewer',
  nodes: [],
  edges: [],
  presence: [],
  cursors: [],
  undoStack: [],
  redoStack: [],

  setBoard: (id, title = '') =>
    set({
      boardId: id, boardTitle: title, nodes: [], edges: [],
      presence: [], cursors: [], undoStack: [], redoStack: [],
    }),

  initFromServer: ({ board, tickets, edges, role }) =>
    set({
      boardTitle: board.title,
      role,
      nodes: tickets.map((t) => ({
        id: t.id,
        type: 'ticket',
        position: { x: t.x, y: t.y },
        data: { text: t.text, color: t.color },
        width: t.width,
        height: t.height,
      })),
      edges: edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        markerEnd: { type: 'arrowclosed' as never },
      })),
      undoStack: [],
      redoStack: [],
    }),

  applyNodeChangesLocally: (changes) => {
    // selection-изменения применяем локально; позиционные приходят через WS-эхо
    const selOnly = changes.filter(
      (c) => c.type === 'select' || c.type === 'dimensions' || c.type === 'remove',
    )
    set({ nodes: applyNodeChanges(selOnly, get().nodes) })
  },

  setEdges: (updater) => set({ edges: updater(get().edges) }),

  remoteTicketCreated: (t) =>
    set((s) => ({
      nodes: s.nodes.some((n) => n.id === t.id) ? s.nodes : [
        ...s.nodes,
        {
          id: t.id,
          type: 'ticket',
          position: { x: t.x, y: t.y },
          data: { text: t.text, color: t.color },
          width: t.width,
          height: t.height,
        },
      ],
    })),

  remoteTicketUpdated: (id, patch) =>
    set((s) => ({
      nodes: s.nodes.map((n) => {
        if (n.id !== id) return n
        const data = { ...n.data }
        if ('text' in patch && patch.text !== undefined) data.text = patch.text
        if ('color' in patch && patch.color !== undefined) data.color = patch.color
        const position = ('x' in patch || 'y' in patch)
          ? {
              x: patch.x !== undefined ? patch.x : n.position.x,
              y: patch.y !== undefined ? patch.y : n.position.y,
            }
          : n.position
        const dims: { width?: number; height?: number } = {}
        if (patch.width !== undefined) dims.width = patch.width
        if (patch.height !== undefined) dims.height = patch.height
        return { ...n, data, position, ...dims }
      }),
    })),

  remoteTicketDeleted: (id) =>
    set((s) => ({
      nodes: s.nodes.filter((n) => n.id !== id),
      edges: s.edges.filter((e) => e.source !== id && e.target !== id),
    })),

  remoteEdgeCreated: (e) =>
    set((s) =>
      s.edges.some((x) => x.id === e.id)
        ? s
        : {
            edges: [
              ...s.edges,
              { id: e.id, source: e.source, target: e.target, markerEnd: { type: 'arrowclosed' as never } },
            ],
          },
    ),

  remoteEdgeDeleted: (id) =>
    set((s) => ({ edges: s.edges.filter((e) => e.id !== id) })),

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

// --- операции: локально + на сервер (оптимистично), эхо подавляем по actor ---

export function createTicket(x: number, y: number, color = STICKER_COLORS[0]) {
  const id = crypto.randomUUID()
  const msg: TicketMsg = { id, x, y, width: 200, height: 100, text: '', color }
  send({ type: 'ticket:create', data: msg })
  useBoard.getState().remoteTicketCreated(msg) // оптимистично
  useBoard.getState().pushUndo({
    undo: () => {
      send({ type: 'ticket:delete', data: { id } })
      useBoard.getState().remoteTicketDeleted(id)
    },
    redo: () => {
      send({ type: 'ticket:create', data: msg })
      useBoard.getState().remoteTicketCreated(msg)
    },
  })
  return id
}

export function updateTicket(id: string, patch: Partial<TicketMsg>, undoPatch?: Partial<TicketMsg>) {
  send({ type: 'ticket:update', data: { id, patch } })
  useBoard.getState().remoteTicketUpdated(id, patch)
  if (undoPatch) {
    useBoard.getState().pushUndo({
      undo: () => {
        send({ type: 'ticket:update', data: { id, patch: undoPatch } })
        useBoard.getState().remoteTicketUpdated(id, undoPatch)
      },
      redo: () => {
        send({ type: 'ticket:update', data: { id, patch } })
        useBoard.getState().remoteTicketUpdated(id, patch)
      },
    })
  }
}

export function deleteTicket(id: string) {
  const node = useBoard.getState().nodes.find((n) => n.id === id)
  if (!node) return
  const snapshot: TicketMsg = {
    id,
    x: node.position.x,
    y: node.position.y,
    width: node.width ?? 200,
    height: node.height ?? 100,
    text: node.data.text,
    color: node.data.color,
  }
  send({ type: 'ticket:delete', data: { id } })
  useBoard.getState().remoteTicketDeleted(id)
  useBoard.getState().pushUndo({
    undo: () => {
      send({ type: 'ticket:create', data: snapshot })
      useBoard.getState().remoteTicketCreated(snapshot)
    },
    redo: () => {
      send({ type: 'ticket:delete', data: { id } })
      useBoard.getState().remoteTicketDeleted(id)
    },
  })
}

export function createEdge(connection: Connection) {
  if (!connection.source || !connection.target || connection.source === connection.target) return
  const id = crypto.randomUUID()
  const msg: EdgeMsg = { id, source: connection.source, target: connection.target }
  send({ type: 'edge:create', data: msg })
  useBoard.getState().remoteEdgeCreated(msg)
  useBoard.getState().pushUndo({
    undo: () => {
      send({ type: 'edge:delete', data: { id } })
      useBoard.getState().remoteEdgeDeleted(id)
    },
    redo: () => {
      send({ type: 'edge:create', data: msg })
      useBoard.getState().remoteEdgeCreated(msg)
    },
  })
}

export function deleteEdge(id: string) {
  const edge = useBoard.getState().edges.find((e) => e.id === id)
  if (!edge) return
  const msg: EdgeMsg = { id, source: edge.source, target: edge.target }
  send({ type: 'edge:delete', data: { id } })
  useBoard.getState().remoteEdgeDeleted(id)
  useBoard.getState().pushUndo({
    undo: () => {
      send({ type: 'edge:create', data: msg })
      useBoard.getState().remoteEdgeCreated(msg)
    },
    redo: () => {
      send({ type: 'edge:delete', data: { id } })
      useBoard.getState().remoteEdgeDeleted(id)
    },
  })
}
