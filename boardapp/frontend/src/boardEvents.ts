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
}

export interface EdgeMsg {
  id: string
  source: string
  target: string
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
}

export const EV = {
  init: 'rf:init',
  ticketCreated: 'rf:ticket-created',
  ticketUpdated: 'rf:ticket-updated',
  ticketDeleted: 'rf:ticket-deleted',
  edgeCreated: 'rf:edge-created',
  edgeDeleted: 'rf:edge-deleted',
  zoneCreated: 'rf:zone-created',
  zoneUpdated: 'rf:zone-updated',
  zoneDeleted: 'rf:zone-deleted',
} as const

export interface ZoneData extends Record<string, unknown> {
  title: string
  color?: string
}

export function ticketToNode(t: TicketMsg): Node<TicketData> {
  return {
    id: t.id,
    type: 'ticket',
    position: { x: t.x, y: t.y },
    data: { text: t.text, color: t.color },
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

export function edgeMsgToEdge(e: EdgeMsg): Edge {
  return {
    id: e.id,
    source: e.source,
    target: e.target,
    type: 'deletable',
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
