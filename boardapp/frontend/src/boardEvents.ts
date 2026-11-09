/* Шина событий канвы: единый поток изменений тикетов и связей.
 * Источники: локальные операции (store.ts) и WS-сообщения (ws.ts).
 * Потребитель: BoardEditorPage применяет их к useNodesState/useEdgesState —
 * канонический контролируемый паттерн React Flow с плавным драгом.
 */
import type { Edge, Node } from '@xyflow/react'
import type { TicketData } from './store'

export interface TicketMsg {
  id: string
  x: number
  y: number
  width: number
  height: number
  text: string
  color: string
  zoneId?: string | null
}

export interface EdgeMsg {
  id: string
  source: string
  target: string
  label?: string
}

export interface ZoneMsg {
  id: string
  title: string
  color?: string
  x: number
  y: number
  width: number
  height: number
}

export interface BoardInitMsg {
  board: { title: string }
  tickets: TicketMsg[]
  edges: EdgeMsg[]
  zones: ZoneMsg[]
  role: string
  presence: Presence[]
  lastSequence?: number
}

export interface Presence {
  userId: string
  username: string
  color: string
}

export type BoardChange =
  | { type: 'ticket:create'; data: TicketMsg }
  | { type: 'ticket:update'; data: { id: string; patch: Partial<TicketMsg> } }
  | { type: 'ticket:delete'; data: { id: string } }
  | { type: 'edge:create'; data: EdgeMsg }
  | { type: 'edge:update'; data: { id: string; label: string } }
  | { type: 'edge:delete'; data: { id: string } }
  | { type: 'zone:create'; data: ZoneMsg }
  | { type: 'zone:update'; data: { id: string; patch: Partial<ZoneMsg> } }
  | { type: 'zone:delete'; data: { id: string } }

export type BoardMutation = BoardChange | { type: 'board:batch'; data: { changes: BoardChange[] } }

export type BoardEvent =
  | { type: 'ticket:created'; data: TicketMsg }
  | { type: 'ticket:updated'; data: { id: string; patch: Partial<TicketMsg> } }
  | { type: 'ticket:deleted'; data: { id: string } }
  | { type: 'edge:created'; data: EdgeMsg }
  | { type: 'edge:updated'; data: { id: string; label: string } }
  | { type: 'edge:deleted'; data: { id: string } }
  | { type: 'zone:created'; data: ZoneMsg }
  | { type: 'zone:updated'; data: { id: string; patch: Partial<ZoneMsg> } }
  | { type: 'zone:deleted'; data: { id: string } }

export const EV = {
  init: 'rf:init',
  ticketCreated: 'rf:ticket-created',
  ticketUpdated: 'rf:ticket-updated',
  ticketDeleted: 'rf:ticket-deleted',
  edgeCreated: 'rf:edge-created',
  edgeUpdated: 'rf:edge-updated',
  edgeDeleted: 'rf:edge-deleted',
  zoneCreated: 'rf:zone-created',
  zoneUpdated: 'rf:zone-updated',
  zoneDeleted: 'rf:zone-deleted',
  nodeDeleteRequest: 'rf:node-delete-request',
} as const

export interface ZoneData extends Record<string, unknown> {
  title: string
  color?: string
}

export interface EdgeData extends Record<string, unknown> {
  label: string
}

export function ticketToNode(t: TicketMsg): Node<TicketData> {
  return {
    id: t.id,
    type: 'ticket',
    position: { x: t.x, y: t.y },
    data: { text: t.text, color: t.color, zoneId: t.zoneId ?? null },
    width: t.width,
    height: t.height,
    zIndex: 5, // тикеты всегда поверх зон
  }
}

export function zoneToNode(z: ZoneMsg): Node<ZoneData> {
  return {
    id: z.id,
    type: 'zone',
    position: { x: z.x, y: z.y },
    data: { title: z.title, color: z.color },
    width: z.width,
    height: z.height,
    zIndex: 0, // подложка
  }
}

export function edgeMsgToEdge(e: EdgeMsg): Edge<EdgeData> {
  return {
    id: e.id,
    source: e.source,
    target: e.target,
    type: 'deletable',
    zIndex: 2,
    data: { label: e.label ?? '' },
    markerEnd: { type: 'arrowclosed' },
  }
}

export function emit(name: string, detail: unknown) {
  window.dispatchEvent(new CustomEvent(name, { detail }))
}

export function on(name: string, handler: (detail: any) => void): () => void {
  const listener = (e: Event) => handler((e as CustomEvent).detail)
  window.addEventListener(name, listener)
  return () => window.removeEventListener(name, listener)
}
