import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  getNodesBounds,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Connection,
  type Edge,
  type Node,
  type XYPosition,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import { ensureUser } from '../api'
import {
  deleteBoardElements, duplicateBoardSelection, insertBoardElements, isTicket, isZone,
  selectedFragment, zoneForTicket,
} from '../boardActions'
import { downloadBoardPng } from '../boardExport'
import { BOARD_TEMPLATES, insertBoardTemplate, type BoardTemplate } from '../boardTemplates'
import DeletableEdge from '../components/DeletableEdge'
import TicketNode from '../components/TicketNode'
import ZoneNode from '../components/ZoneNode'
import ShareModal from '../components/ShareModal'
import Toolbar from '../components/Toolbar'
import SiteStrip from '../components/SiteStrip'
import { EV, on, type BoardChange, type TicketMsg, type ZoneMsg } from '../boardEvents'
import {
  STICKER_COLORS,
  ZONE_COLORS,
  applyTicketUpdated,
  commitBatch,
  createEdge,
  createTicket,
  createZone,
  ticketAutoHeight,
  useBoard,
  type TicketData,
} from '../store'
import { connectBoard, disconnect, sendCursorThrottled, setMyUserId } from '../ws'

const nodeTypes = { ticket: TicketNode, zone: ZoneNode }
const edgeTypes = { deletable: DeletableEdge }

export default function BoardEditorPage() {
  return (
    <ReactFlowProvider>
      <BoardEditorInner />
    </ReactFlowProvider>
  )
}

function BoardEditorInner() {
  const { id } = useParams<{ id: string }>()
  const nav = useNavigate()
  const { screenToFlowPosition } = useReactFlow()

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])

  const role = useBoard((s) => s.role)
  const boardTitle = useBoard((s) => s.boardTitle)
  const cursors = useBoard((s) => s.cursors)
  const presence = useBoard((s) => s.presence)
  const resetBoard = useBoard((s) => s.reset)
  const undo = useBoard((s) => s.undo)
  const redo = useBoard((s) => s.redo)

  const [shareOpen, setShareOpen] = useState(false)
  const [actionError, setActionError] = useState('')
  const [colorIdx, setColorIdx] = useState(0)
  const zoneColorIdx = useRef(0)
  const dragStart = useRef(new Map<string, Node>())
  const viewportRef = useRef<HTMLDivElement | null>(null)
  const nodesRef = useRef(nodes)
  nodesRef.current = nodes
  const edgesRef = useRef(edges)
  edgesRef.current = edges

  const editable = role === 'owner' || role === 'editor'

  useEffect(() => {
    if (!id) return
    ensureUser().then((me) => { if (me) setMyUserId(me.id) })
    resetBoard()
    setActionError('')
    setNodes([])
    setEdges([])
    connectBoard(id)
    return () => disconnect()
  }, [id])

  // единый поток изменений канвы → локальное состояние (React Flow canonical)
  useEffect(() => {
    const offs = [
      on(EV.init, ({ nodes: initNodes, edges: initEdges }) => {
        setNodes((initNodes as Node[]).map((n) =>
          n.type === 'ticket'
            ? { ...n, height: ticketAutoHeight(String((n.data as TicketData).text ?? '')) }
            : n))
        setEdges(initEdges)
      }),
      on(EV.ticketCreated, (node: Node<TicketData>) => {
        setNodes((ns: Node[]) => (ns.some((n) => n.id === node.id) ? ns : [...ns, node]))
      }),
      on(EV.ticketUpdated, ({ id: tid, patch }: { id: string; patch: Partial<TicketMsg> & { editing?: boolean } }) => {
        setNodes((ns: Node[]) => ns.map((n) => {
          if (n.id !== tid) return n
          const data = { ...n.data } as TicketData
          if (patch.text !== undefined) data.text = patch.text
          if (patch.color !== undefined) data.color = patch.color
          if (patch.zoneId !== undefined) data.zoneId = patch.zoneId
          if (patch.editing !== undefined) data.editing = patch.editing
          const position = (patch.x !== undefined || patch.y !== undefined)
            ? {
                x: patch.x !== undefined ? patch.x : n.position.x,
                y: patch.y !== undefined ? patch.y : n.position.y,
              }
            : n.position
          // авторост высоты под текст, если сервер/локальная правка не принесла свою
          const height = (patch.height !== undefined)
            ? patch.height
            : (patch.text !== undefined ? ticketAutoHeight(patch.text) : n.height)
          return { ...n, data, position, height }
        }))
      }),
      on(EV.ticketDeleted, ({ id: tid }: { id: string }) => {
        setNodes((ns) => ns.filter((n) => n.id !== tid))
        setEdges((es) => es.filter((e) => e.source !== tid && e.target !== tid))
      }),
      on(EV.edgeCreated, (edge: Edge) => {
        setEdges((es) => (es.some((x) => x.id === edge.id) ? es : [...es, edge]))
      }),
      on(EV.edgeUpdated, ({ id, label }: { id: string; label: string }) => {
        setEdges((es) => es.map((edge) => edge.id === id ? { ...edge, data: { ...edge.data, label } } : edge))
      }),
      on(EV.edgeDeleted, ({ id: eid }: { id: string }) => {
        setEdges((es) => es.filter((e) => e.id !== eid))
      }),
      on(EV.zoneCreated, (node: Node) => {
        setNodes((ns: Node[]) => (ns.some((n) => n.id === node.id) ? ns : [...ns, node]))
      }),
      on(EV.zoneUpdated, ({ id: zid, patch }: { id: string; patch: Partial<ZoneMsg> }) => {
        setNodes((ns: Node[]) => ns.map((n) => {
          if (n.id !== zid) return n
          const data = { ...n.data } as { title?: string; color?: string }
          if (patch.title !== undefined) data.title = patch.title
          if (patch.color !== undefined) data.color = patch.color
          const position = (patch.x !== undefined || patch.y !== undefined)
            ? {
                x: patch.x !== undefined ? patch.x : n.position.x,
                y: patch.y !== undefined ? patch.y : n.position.y,
              }
            : n.position
          const dims: { width?: number; height?: number } = {}
          if (patch.width !== undefined) dims.width = patch.width
          if (patch.height !== undefined) dims.height = patch.height
          return { ...n, data, position, ...dims }
        }))
      }),
      on(EV.zoneDeleted, ({ id: zid }: { id: string }) => {
        setNodes((ns) => ns.filter((n) => n.id !== zid).map((n) =>
          isTicket(n) && n.data.zoneId === zid ? { ...n, data: { ...n.data, zoneId: null } } : n,
        ))
      }),
      on(EV.nodeDeleteRequest, ({ id: rid }: { id: string }) => {
        const node = nodesRef.current.find((item) => item.id === rid)
        if (node) deleteBoardElements([node], [], nodesRef.current, edgesRef.current)
      }),
    ]
    return () => offs.forEach((off) => off())
  }, [])

  const onConnect = useCallback(
    (c: Connection) => {
      if (!editable) return
      createEdge(c)
    },
    [editable],
  )

  const startDrag = useCallback((dragged: Node[]) => {
    dragStart.current = new Map(dragged.map((node) => [node.id, { ...node, position: { ...node.position } }]))
  }, [])

  const stopDrag = useCallback((dragged: Node[]) => {
    const changes: BoardChange[] = []
    const inverse: BoardChange[] = []
    const positions = new Map(dragged.map((node) => [node.id, node.position]))
    const zones = nodesRef.current.filter(isZone).map((zone) => ({
      ...zone, position: positions.get(zone.id) ?? zone.position,
    }))
    function moveTicket(ticket: Node<TicketData>, position: XYPosition, zoneId = ticket.data.zoneId) {
      if (ticket.position.x === position.x && ticket.position.y === position.y) return
      const patch: Partial<TicketMsg> = { ...position }
      const before: Partial<TicketMsg> = { ...ticket.position }
      if (zoneId !== ticket.data.zoneId) {
        patch.zoneId = zoneId
        before.zoneId = ticket.data.zoneId
      }
      changes.push({ type: 'ticket:update', data: { id: ticket.id, patch } })
      inverse.push({ type: 'ticket:update', data: { id: ticket.id, patch: before } })
    }
    for (const node of dragged) {
      const start = dragStart.current.get(node.id)
      if (!start || (start.position.x === node.position.x && start.position.y === node.position.y)) continue
      if (isTicket(start) && isTicket(node)) {
        const zoneId = zoneForTicket(zones, node.position, node.width, node.height, node.data.zoneId)
        moveTicket({ ...start, data: node.data }, node.position, zoneId)
      }
      if (isZone(start)) {
        changes.push({ type: 'zone:update', data: { id: node.id, patch: node.position } })
        inverse.push({ type: 'zone:update', data: { id: node.id, patch: start.position } })
        const dx = node.position.x - start.position.x
        const dy = node.position.y - start.position.y
        for (const ticket of nodesRef.current.filter(isTicket)) {
          if (ticket.data.zoneId === node.id && !positions.has(ticket.id)) {
            moveTicket(ticket, { x: ticket.position.x + dx, y: ticket.position.y + dy })
          }
        }
      }
    }
    dragStart.current.clear()
    commitBatch(changes, inverse)
  }, [])

  const selectNodes = useCallback((ids: string[]) => {
    const selected = new Set(ids)
    setNodes((all) => all.map((node) =>
      Boolean(node.selected) === selected.has(node.id) ? node : { ...node, selected: selected.has(node.id) },
    ))
    setEdges((all) => all.map((edge) => edge.selected ? { ...edge, selected: false } : edge))
  }, [setNodes, setEdges])

  const duplicateSelection = useCallback(() => {
    if (!editable || !nodesRef.current.some((node) => node.selected)) return false
    selectNodes(duplicateBoardSelection(nodesRef.current, edgesRef.current))
    return true
  }, [editable, selectNodes])

  const createLinkedTicket = useCallback(() => {
    const selected = nodesRef.current.filter((node) => node.selected)
    const source = selected[0]
    if (!editable || selected.length !== 1 || !isTicket(source)) return false
    const id = crypto.randomUUID()
    const position = { x: source.position.x + (source.width ?? 200) + 100, y: source.position.y }
    const zoneId = zoneForTicket(nodesRef.current, position, 200, 130, source.data.zoneId)
    insertBoardElements({
      tickets: [{ id, ...position, text: '', width: 200, height: 130, color: source.data.color, zoneId }],
      edges: [{ id: crypto.randomUUID(), source: source.id, target: id }],
    })
    selectNodes([id])
    applyTicketUpdated(id, { editing: true })
    return true
  }, [editable, selectNodes])

  function updateSelectedTickets(
    patchFor: (node: Node<TicketData>) => Partial<Pick<TicketMsg, 'x' | 'y' | 'color' | 'zoneId'>>,
  ) {
    const changes: BoardChange[] = []
    const inverse: BoardChange[] = []
    for (const node of nodesRef.current.filter(isTicket).filter((node) => node.selected)) {
      const patch = patchFor(node)
      if (Object.keys(patch).length === 0) continue
      const before = { ...node.position, color: node.data.color, zoneId: node.data.zoneId }
      changes.push({ type: 'ticket:update', data: { id: node.id, patch } })
      const undoPatch = Object.fromEntries(
        (Object.keys(patch) as (keyof typeof before)[]).map((key) => [key, before[key]]),
      )
      inverse.push({ type: 'ticket:update', data: { id: node.id, patch: undoPatch } })
    }
    commitBatch(changes, inverse)
  }

  function alignTickets(axis: 'x' | 'y') {
    const tickets = nodesRef.current.filter(isTicket).filter((node) => node.selected)
    const coordinate = Math.min(...tickets.map((node) => node.position[axis]))
    updateSelectedTickets((node) => {
      if (node.position[axis] === coordinate) return {}
      const position = { ...node.position, [axis]: coordinate }
      const zoneId = zoneForTicket(nodesRef.current, position, node.width, node.height, node.data.zoneId)
      return zoneId === node.data.zoneId ? { [axis]: coordinate } : { [axis]: coordinate, zoneId }
    })
  }

  function createZoneFromSelection() {
    const tickets = nodesRef.current.filter(isTicket).filter((node) => node.selected)
    if (tickets.length === 0) return
    const bounds = getNodesBounds(tickets)
    const width = Math.max(240, bounds.width + 80)
    const height = Math.max(140, bounds.height + 100)
    if (width > 8000 || height > 8000) {
      setActionError('Карточки расположены слишком далеко друг от друга для одной группы.')
      return
    }
    const id = crypto.randomUUID()
    const zone: ZoneMsg = {
      id, title: '', color: ZONE_COLORS[zoneColorIdx.current % ZONE_COLORS.length],
      x: bounds.x - 40, y: bounds.y - 60, width, height,
    }
    zoneColorIdx.current += 1
    const changes: BoardChange[] = [{ type: 'zone:create', data: zone }]
    const inverse: BoardChange[] = []
    for (const ticket of tickets) {
      changes.push({ type: 'ticket:update', data: { id: ticket.id, patch: { zoneId: id } } })
      inverse.push({ type: 'ticket:update', data: { id: ticket.id, patch: { zoneId: ticket.data.zoneId } } })
    }
    inverse.push({ type: 'zone:delete', data: { id } })
    setActionError('')
    commitBatch(changes, inverse)
    selectNodes([id])
  }

  const onMove = useCallback((_: unknown, pos: XYPosition) => {
    sendCursorThrottled(pos.x, pos.y)
  }, [])

  const canvasCenter = useCallback(() => {
    const rect = viewportRef.current?.getBoundingClientRect()
    return screenToFlowPosition({
      x: rect ? rect.left + rect.width / 2 : window.innerWidth / 2,
      y: rect ? rect.top + rect.height / 2 : window.innerHeight / 2,
    })
  }, [screenToFlowPosition])

  function addTicketAt(center: XYPosition) {
    const position = { x: center.x - 100, y: center.y - 65 }
    const zoneId = zoneForTicket(nodesRef.current, position)
    createTicket(position.x, position.y, STICKER_COLORS[colorIdx % STICKER_COLORS.length], zoneId)
    setColorIdx((i) => i + 1)
  }

  function addZoneToCenter() {
    const center = canvasCenter()
    createZone(center.x - 210, center.y - 140, '',
      ZONE_COLORS[zoneColorIdx.current % ZONE_COLORS.length])
    zoneColorIdx.current += 1
  }

  function onWrapperDoubleClick(event: React.MouseEvent) {
    if (!editable || !(event.target instanceof Element) || !event.target.matches('.react-flow__pane')) return
    addTicketAt(screenToFlowPosition({ x: event.clientX, y: event.clientY }))
  }

  async function exportPng(selection = false) {
    const viewport = viewportRef.current?.querySelector<HTMLElement>('.react-flow__viewport')
    const fragment = selection ? selectedFragment(nodesRef.current) : nodesRef.current
    if (!viewport || fragment.length === 0) return
    setActionError('')
    try {
      const title = useBoard.getState().boardTitle || 'board'
      await downloadBoardPng(viewport, fragment, edgesRef.current, title + (selection ? '-фрагмент.png' : '.png'))
    } catch {
      setActionError('Не удалось скачать PNG.')
    }
  }

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (!editable || !(e.ctrlKey || e.metaKey) || e.defaultPrevented) return
      if (e.target instanceof HTMLElement && e.target.closest('input, textarea, [contenteditable]:not([contenteditable="false"])')) return
      const key = e.key.toLowerCase()
      if (!e.shiftKey && !e.repeat && (
        (key === 'd' && duplicateSelection()) || (key === 'arrowright' && createLinkedTicket())
      )) {
        e.preventDefault()
        e.stopPropagation()
      }
      if (key === 'z') {
        e.preventDefault()
        if (e.shiftKey) redo()
        else undo()
      }
    }
    window.addEventListener('keydown', onKey, true)
    return () => window.removeEventListener('keydown', onKey, true)
  }, [editable, duplicateSelection, createLinkedTicket, undo, redo])

  const cursorLabels = useMemo(
    () =>
      cursors.map((c) => (
        <div
          key={c.userId}
          className="cursor-label"
          style={{ left: c.x, top: c.y, ['--cursor-color' as string]: c.color }}
        >
          {presence.find((p) => p.userId === c.userId)?.username ?? '?'}
        </div>
      )),
    [cursors, presence],
  )

  const selection = nodes.filter((node) => node.selected)
  const selectedTickets = selection.filter(isTicket)
  const canLink = selection.length === 1 && selectedTickets.length === 1

  if (!id) {
    nav('/')
    return null
  }

  return (
    <main className="editor-with-strip">
    <SiteStrip title={boardTitle} />
    <div className="editor-wrap" ref={viewportRef} onDoubleClick={onWrapperDoubleClick}>
      <Toolbar onExport={() => { void exportPng() }} />
      {role === 'owner' && (
        <div className="toolbar" role="toolbar" aria-label="Доступ к доске" style={{ left: 'auto', right: 12 }}>
          <button type="button" className="btn" aria-haspopup="dialog" onClick={() => setShareOpen(true)}>Поделиться</button>
        </div>
      )}
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onBeforeDelete={async ({ nodes: deleted, edges: links }) => {
          if (editable) deleteBoardElements(deleted, links, nodesRef.current, edgesRef.current)
          return false
        }}
        onConnect={onConnect}
        onNodeDragStart={(_, _node, dragged) => startDrag(dragged)}
        onNodeDragStop={(_, _node, dragged) => stopDrag(dragged)}
        onMove={onMove}
        nodesDraggable={editable}
        nodesConnectable={editable}
        edgesFocusable={editable}
        snapToGrid
        snapGrid={[20, 20]}
        elevateNodesOnSelect={false}
        elevateEdgesOnSelect={false}
        panOnScroll
        zoomOnScroll
        selectionOnDrag={editable}
        panOnDrag={editable ? [1, 2] : true}
        deleteKeyCode={editable ? ['Backspace', 'Delete'] : null}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
        <MiniMap />
        <Controls />
      </ReactFlow>
      <div className="board-tools">
        {editable && (
          <div className="toolbar" aria-label="Добавить на доску">
            <button className="btn" onClick={() => addTicketAt(canvasCenter())}>+ Тикет</button>
            <button className="btn ghost" onClick={addZoneToCenter}>+ Группа</button>
            <select className="btn ghost board-tool-select" aria-label="Вставить шаблон" value=""
              onChange={(event) => {
                const template = event.target.value as BoardTemplate
                if (template) selectNodes(insertBoardTemplate(template, canvasCenter()))
              }}>
              <option value="" disabled>Вставить шаблон…</option>
              {BOARD_TEMPLATES.map(({ id, name }) => <option key={id} value={id}>{name}</option>)}
            </select>
          </div>
        )}
        {selection.length > 0 && (
          <div className="toolbar selection-toolbar" aria-label="Действия с выделением">
            {editable && (
              <>
                <button className="btn ghost" title="Ctrl+D" onClick={duplicateSelection}>Дублировать</button>
                {canLink && (
                  <button className="btn ghost" title="Ctrl+→" onClick={createLinkedTicket}>+ Связанный тикет</button>
                )}
                {selectedTickets.length > 1 && (
                  <>
                    <button className="btn ghost" onClick={() => alignTickets('x')}>По левому краю</button>
                    <button className="btn ghost" onClick={() => alignTickets('y')}>По верхнему краю</button>
                  </>
                )}
                {selectedTickets.length > 0 && (
                  <>
                    <select className="btn ghost board-tool-select" aria-label="Цвет выделенных тикетов" value=""
                      onChange={(event) => {
                        const color = event.target.value
                        if (color) updateSelectedTickets((ticket) => ticket.data.color === color ? {} : { color })
                      }}>
                      <option value="" disabled>Цвет тикетов…</option>
                      {['Жёлтый', 'Оранжевый', 'Зелёный', 'Голубой', 'Сиреневый', 'Розовый'].map((name, index) =>
                        <option key={name} value={STICKER_COLORS[index]}>{name}</option>,
                      )}
                    </select>
                    <button className="btn ghost" onClick={createZoneFromSelection}>Создать группу</button>
                  </>
                )}
              </>
            )}
            <button className="btn ghost" onClick={() => { void exportPng(true) }}>Скачать PNG выделения</button>
          </div>
        )}
        {actionError && <div className="toolbar" role="alert">{actionError}</div>}
      </div>
      {cursorLabels}
      {shareOpen && <ShareModal boardId={id} onClose={() => setShareOpen(false)} />}
    </div>
    </main>
  )
}
