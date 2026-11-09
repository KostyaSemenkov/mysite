import type { Edge, Node, XYPosition } from '@xyflow/react'
import type { BoardChange, EdgeMsg, TicketMsg, ZoneData, ZoneMsg } from './boardEvents'
import { commitBatch, ticketAutoHeight, type TicketData } from './store'

export function isTicket(node: Node): node is Node<TicketData, 'ticket'> {
  return node.type === 'ticket'
}

export function isZone(node: Node): node is Node<ZoneData, 'zone'> {
  return node.type === 'zone'
}

export function ticketSnapshot(node: Node<TicketData>): TicketMsg {
  const { text, color, zoneId } = node.data
  return {
    id: node.id, ...node.position, text, color, zoneId,
    width: node.width ?? 200, height: node.height ?? ticketAutoHeight(text),
  }
}

export function zoneSnapshot(node: Node<ZoneData>): ZoneMsg {
  return {
    id: node.id, ...node.position, title: node.data.title, color: node.data.color,
    width: node.width ?? 420, height: node.height ?? 280,
  }
}

function edgeSnapshot(edge: Edge): EdgeMsg {
  return {
    id: edge.id, source: edge.source, target: edge.target,
    label: typeof edge.data?.label === 'string' ? edge.data.label : '',
  }
}

export function zoneForTicket(
  nodes: Node[], position: XYPosition, width = 200, height = 130, current: string | null = null,
) {
  const cx = position.x + width / 2
  const cy = position.y + height / 2
  const candidates = nodes.filter(isZone).map(zoneSnapshot).filter((zone) =>
    cx >= zone.x && cx <= zone.x + zone.width && cy >= zone.y && cy <= zone.y + zone.height,
  )
  if (candidates.some((zone) => zone.id === current)) return current
  candidates.sort((a, b) => a.width * a.height - b.width * b.height || a.id.localeCompare(b.id))
  return candidates[0]?.id ?? null
}

// Selecting a zone includes its members when copying or exporting it.
export function selectedFragment(nodes: Node[]) {
  const zoneIds = new Set(nodes.filter((node) => node.selected && isZone(node)).map((node) => node.id))
  return nodes.filter((node) => node.selected || (isTicket(node) && zoneIds.has(node.data.zoneId ?? '')))
}

interface BoardElements {
  zones?: ZoneMsg[]
  tickets: TicketMsg[]
  edges?: EdgeMsg[]
}

export function insertBoardElements({ zones = [], tickets, edges = [] }: BoardElements) {
  const changes: BoardChange[] = [
    ...zones.map((data): BoardChange => ({ type: 'zone:create', data })),
    ...tickets.map((data): BoardChange => ({ type: 'ticket:create', data })),
    ...edges.map((data): BoardChange => ({ type: 'edge:create', data })),
  ]
  const inverse: BoardChange[] = [
    ...tickets.map(({ id }): BoardChange => ({ type: 'ticket:delete', data: { id } })),
    ...zones.map(({ id }): BoardChange => ({ type: 'zone:delete', data: { id } })),
  ]
  commitBatch(changes, inverse)
  return [...zones, ...tickets].map(({ id }) => id)
}

export function duplicateBoardSelection(nodes: Node[], edges: Edge[]) {
  const fragment = selectedFragment(nodes)
  const ids = new Map<string, string>(fragment.map((node) => [node.id, crypto.randomUUID()]))
  const offset = ({ x, y }: XYPosition) => ({ x: x + 40, y: y + 40 })
  const zones = fragment.filter(isZone).map((node) => ({
    ...zoneSnapshot(node), ...offset(node.position), id: ids.get(node.id)!,
  }))
  const tickets = fragment.filter(isTicket).map((node) => {
    const ticket = ticketSnapshot(node)
    const position = offset(node.position)
    const zoneId = (ticket.zoneId && ids.get(ticket.zoneId))
      || zoneForTicket(nodes, position, ticket.width, ticket.height, node.data.zoneId)
    return { ...ticket, ...position, id: ids.get(node.id)!, zoneId }
  })
  const links = edges.filter(({ source, target }) => ids.has(source) && ids.has(target)).map((edge) => ({
    ...edgeSnapshot(edge), id: crypto.randomUUID(), source: ids.get(edge.source)!, target: ids.get(edge.target)!,
  }))
  insertBoardElements({ zones, tickets, edges: links })
  // Keep the same selection shape, so a copied zone stays selected as a unit.
  return fragment.filter((node) => node.selected).map((node) => ids.get(node.id)!)
}

export function deleteBoardElements(deleted: Node[], links: Edge[], allNodes: Node[], allEdges: Edge[]) {
  const tickets = deleted.filter(isTicket)
  const zones = deleted.filter(isZone)
  const ticketIds = new Set(tickets.map(({ id }) => id))
  const zoneIds = new Set(zones.map(({ id }) => id))
  const linkIds = new Set(links.map(({ id }) => id))
  const touchesDeletedTicket = (edge: Edge) => ticketIds.has(edge.source) || ticketIds.has(edge.target)
  const affectedLinks = allEdges.filter((edge) => linkIds.has(edge.id) || touchesDeletedTicket(edge))
  const survivors = allNodes.filter(isTicket).filter(({ id, data }) =>
    !ticketIds.has(id) && zoneIds.has(data.zoneId ?? ''),
  )
  const changes: BoardChange[] = [
    ...affectedLinks.filter((edge) => !touchesDeletedTicket(edge)).map(({ id }): BoardChange =>
      ({ type: 'edge:delete', data: { id } })),
    ...tickets.map(({ id }): BoardChange => ({ type: 'ticket:delete', data: { id } })),
    ...zones.map(({ id }): BoardChange => ({ type: 'zone:delete', data: { id } })),
  ]
  const inverse: BoardChange[] = [
    ...zones.map((node): BoardChange => ({ type: 'zone:create', data: zoneSnapshot(node) })),
    ...tickets.map((node): BoardChange => ({ type: 'ticket:create', data: ticketSnapshot(node) })),
    ...survivors.map(({ id, data }): BoardChange =>
      ({ type: 'ticket:update', data: { id, patch: { zoneId: data.zoneId } } })),
    ...affectedLinks.map((edge): BoardChange => ({ type: 'edge:create', data: edgeSnapshot(edge) })),
  ]
  commitBatch(changes, inverse)
}
