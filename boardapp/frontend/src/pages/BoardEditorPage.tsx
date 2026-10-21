import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  addEdge,
  getNodesBounds,
  getViewportForBounds,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type OnSelectionChangeParams,
  type XYPosition,
} from '@xyflow/react'
import { toPng } from 'html-to-image'
import '@xyflow/react/dist/style.css'

import { ensureUser } from '../api'
import DeletableEdge from '../components/DeletableEdge'
import TicketNode from '../components/TicketNode'
import ZoneNode from '../components/ZoneNode'
import ShareModal from '../components/ShareModal'
import Toolbar from '../components/Toolbar'
import { EV, on, type TicketMsg, type ZoneMsg } from '../boardEvents'
import {
  STICKER_COLORS,
  ZONE_COLORS,
  createEdge,
  createTicket,
  createZone,
  deleteEdgeWithSnapshot,
  deleteTicketWithSnapshot,
  deleteZoneWithSnapshot,
  ticketAutoHeight,
  updateTicket,
  updateZone,
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
  const cursors = useBoard((s) => s.cursors)
  const presence = useBoard((s) => s.presence)
  const resetBoard = useBoard((s) => s.reset)
  const undo = useBoard((s) => s.undo)
  const redo = useBoard((s) => s.redo)

  const [shareOpen, setShareOpen] = useState(false)
  const [colorIdx, setColorIdx] = useState(0)
  const zoneColorIdx = useRef(0)
  const dragStart = useRef<Record<string, { x: number; y: number }>>({})
  const zoneContents = useRef<Record<string, { id: string; x: number; y: number }[]>>({})
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
        setNodes((ns) => ns.filter((n) => n.id !== zid))
      }),
    ]
    return () => offs.forEach((off) => off())
  }, [])

  const onConnect = useCallback(
    (c: Connection) => {
      if (!editable) return
      createEdge(c)
      setEdges((eds) => addEdge(c, eds))
    },
    [editable, setEdges],
  )

  const onEdgesDelete = useCallback((changes: EdgeChange[]) => {
    if (!editable) return
    changes.forEach((c) => {
      if (c.type === 'remove') {
        const snap = edgesRef.current.find((e) => e.id === c.id)
        if (snap) deleteEdgeWithSnapshot({ id: snap.id, source: snap.source, target: snap.target })
      }
    })
  }, [editable])

  const onNodeDragStart = useCallback(
    (_: MouseEvent | TouchEvent, node: Node) => {
      dragStart.current[node.id] = { ...node.position }
      if (node.type === 'zone') {
        // запоминаем тикеты, чей центр внутри зоны, — поедут вместе с ней
        const zw = node.width ?? 420
        const zh = node.height ?? 280
        zoneContents.current[node.id] = nodesRef.current
          .filter((n) => n.type === 'ticket')
          .filter((n) => {
            const cx = n.position.x + (n.width ?? 200) / 2
            const cy = n.position.y + (n.height ?? 100) / 2
            return cx >= node.position.x && cx <= node.position.x + zw
              && cy >= node.position.y && cy <= node.position.y + zh
          })
          .map((n) => ({ id: n.id, x: n.position.x, y: n.position.y }))
      }
    }, [])

  const onNodeDragStop = useCallback(
    (_: MouseEvent | TouchEvent, node: Node) => {
      const start = dragStart.current[node.id]
      if (!start) return
      const dx = node.position.x - start.x
      const dy = node.position.y - start.y
      if (node.type === 'zone') {
        if (dx !== 0 || dy !== 0) {
          updateZone(node.id, { x: node.position.x, y: node.position.y },
            { x: start.x, y: start.y })
          // вложенные тикеты переезжают вместе с зоной (без отдельных undo-точек)
          const contents = zoneContents.current[node.id] ?? []
          for (const t of contents) {
            updateTicket(t.id, { x: t.x + dx, y: t.y + dy })
          }
        }
        delete zoneContents.current[node.id]
        delete dragStart.current[node.id]
        return
      }
      if (start.x === node.position.x && start.y === node.position.y) return
      // одна undo-операция на весь drag
      updateTicket(node.id, { x: node.position.x, y: node.position.y },
        { x: start.x, y: start.y })
      delete dragStart.current[node.id]
    }, [])

  const onSelectionChange = useCallback(({ nodes: selNodes, edges: selEdges }: OnSelectionChangeParams) => {
    void selNodes
    void selEdges
  }, [])

  const onNodesDelete = useCallback((deleted: Node[]) => {
    if (!editable) return
    deleted.forEach((n) => {
      if (n.type === 'zone') {
        deleteZoneWithSnapshot(n as unknown as {
          id: string; position: { x: number; y: number };
          width?: number; height?: number; data: { title: string };
        })
      } else {
        deleteTicketWithSnapshot(n as unknown as {
          id: string; position: { x: number; y: number };
          width?: number; height?: number; data: TicketData;
        })
      }
    })
  }, [editable])

  const onMove = useCallback((_: unknown, pos: XYPosition) => {
    sendCursorThrottled(pos.x, pos.y)
  }, [])

  const addTicketToCenter = useCallback(() => {
    if (!editable) return
    const center = screenToFlowPosition({ x: window.innerWidth / 2, y: window.innerHeight / 2 })
    createTicket(center.x - 100, center.y - 50, STICKER_COLORS[colorIdx % STICKER_COLORS.length])
    setColorIdx((i) => i + 1)
  }, [editable, screenToFlowPosition, colorIdx])

  const addZoneToCenter = useCallback(() => {
    if (!editable) return
    const center = screenToFlowPosition({ x: window.innerWidth / 2, y: window.innerHeight / 2 })
    createZone(center.x - 210, center.y - 140, '',
      ZONE_COLORS[zoneColorIdx.current % ZONE_COLORS.length])
    zoneColorIdx.current += 1
  }, [editable, screenToFlowPosition])

  const onWrapperDoubleClick = useCallback((event: React.MouseEvent) => {
    if (!editable) return
    // двойной клик по пустой канве (не по ноде)
    const target = event.target as HTMLElement
    if (!target.classList.contains('react-flow__pane')) return
    const position = screenToFlowPosition({ x: event.clientX, y: event.clientY })
    createTicket(position.x - 100, position.y - 50, STICKER_COLORS[colorIdx % STICKER_COLORS.length])
    setColorIdx((i) => i + 1)
  }, [editable, screenToFlowPosition, colorIdx])

  const exportPng = useCallback(async () => {
    const viewport = viewportRef.current?.querySelector('.react-flow__viewport') as HTMLElement | null
    if (!viewport) return
    const currentNodes = nodesRef.current
    if (currentNodes.length === 0) return
    const bounds = getNodesBounds(currentNodes)
    const width = Math.ceil(bounds.width) + 200
    const height = Math.ceil(bounds.height) + 200
    const vp = getViewportForBounds(bounds, width, height, 0.4, 2, 100)
    const dataUrl = await toPng(viewport, {
      backgroundColor: '#ffffff',
      width,
      height,
      style: {
        width: `${width}px`,
        height: `${height}px`,
        transform: `translate(${vp.x}px, ${vp.y}px) scale(${vp.zoom})`,
      },
    })
    const a = document.createElement('a')
    a.download = `${useBoard.getState().boardTitle || 'board'}.png`
    a.href = dataUrl
    a.click()
  }, [])

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (!(e.ctrlKey || e.metaKey)) return
      if (e.key.toLowerCase() === 'z') {
        e.preventDefault()
        if (e.shiftKey) redo()
        else undo()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [undo, redo])

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

  if (!id) {
    nav('/')
    return null
  }

  return (
    <div className="editor-wrap" ref={viewportRef} onDoubleClick={onWrapperDoubleClick}>
      <Toolbar onExport={exportPng} />
      {role === 'owner' && (
        <div className="toolbar" style={{ left: 'auto', right: 12 }}>
          <button className="btn" onClick={() => setShareOpen(true)}>Поделиться</button>
        </div>
      )}
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={(changes) => {
          onEdgesDelete(changes)
          onEdgesChange(changes)
        }}
        onConnect={onConnect}
        onNodeDragStart={onNodeDragStart}
        onNodeDragStop={onNodeDragStop}
        onNodesDelete={onNodesDelete}
        onSelectionChange={onSelectionChange}
        onMove={onMove}
        nodesDraggable={editable}
        nodesConnectable={editable}
        edgesFocusable={editable}
        snapToGrid
        snapGrid={[20, 20]}
        elevateNodesOnSelect={false}
        panOnScroll
        zoomOnScroll
        selectionOnDrag={false}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
        <MiniMap />
        <Controls />
      </ReactFlow>
      {editable && (
        <div className="toolbar" style={{ top: 'auto', bottom: 12 }}>
          <button className="btn" onClick={addTicketToCenter}>+ Тикет</button>
          <button className="btn ghost" onClick={addZoneToCenter}>+ Зона</button>
        </div>
      )}
      {cursorLabels}
      {shareOpen && <ShareModal boardId={id} onClose={() => setShareOpen(false)} />}
    </div>
  )
}
