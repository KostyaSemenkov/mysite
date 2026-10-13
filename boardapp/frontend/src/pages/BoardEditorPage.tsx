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
  useReactFlow,
  type Connection,
  type EdgeChange,
  type Node,
  type NodeTypes,
  type OnSelectionChangeParams,
  type XYPosition,
} from '@xyflow/react'
import { toPng } from 'html-to-image'
import '@xyflow/react/dist/style.css'

import { getCurrentUser } from '../api'
import TicketNode from '../components/TicketNode'
import ShareModal from '../components/ShareModal'
import Toolbar from '../components/Toolbar'
import {
  STICKER_COLORS,
  createEdge,
  createTicket,
  deleteEdge,
  deleteTicket,
  updateTicket,
  useBoard,
  type TicketData,
} from '../store'
import { connectBoard, disconnect, sendCursorThrottled, setMyUserId } from '../ws'

const nodeTypes: NodeTypes = { ticket: TicketNode }

// React Flow использует DOM-события в drag-хендлерах
type FlowDragEvent = MouseEvent | TouchEvent

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
  const me = getCurrentUser()
  const { screenToFlowPosition } = useReactFlow()

  const nodes = useBoard((s) => s.nodes)
  const edges = useBoard((s) => s.edges)
  const role = useBoard((s) => s.role)
  const cursors = useBoard((s) => s.cursors)
  const setBoard = useBoard((s) => s.setBoard)
  const applyNodeChangesLocally = useBoard((s) => s.applyNodeChangesLocally)
  const setEdges = useBoard((s) => s.setEdges)
  const undo = useBoard((s) => s.undo)
  const redo = useBoard((s) => s.redo)

  const [shareOpen, setShareOpen] = useState(false)
  const [colorIdx, setColorIdx] = useState(0)
  const dragStart = useRef<Record<string, { x: number; y: number }>>({})
  const viewportRef = useRef<HTMLDivElement | null>(null)

  const editable = role === 'owner' || role === 'editor'

  useEffect(() => {
    if (!id) return
    if (me) setMyUserId(me.id)
    setBoard(id)
    connectBoard(id)
    return () => disconnect()
  }, [id])

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
      if (c.type === 'remove') deleteEdge(c.id)
    })
  }, [editable])

  const onNodeDragStart = useCallback(
    (_: FlowDragEvent, node: Node<TicketData>) => {
      dragStart.current[node.id] = { ...node.position }
    }, [])

  const onNodeDragStop = useCallback(
    (_: FlowDragEvent, node: Node<TicketData>) => {
      const start = dragStart.current[node.id]
      if (!start) return
      if (start.x === node.position.x && start.y === node.position.y) return
      // одна undo-операция на весь drag
      updateTicket(node.id, { x: node.position.x, y: node.position.y },
        { x: start.x, y: start.y })
      delete dragStart.current[node.id]
    }, [])

  const onSelectionChange = useCallback(({ nodes, edges }: OnSelectionChangeParams) => {
    // удаление выделенного через Delete обрабатывают сами React Flow changes
    void nodes
    void edges
  }, [])

  const onNodesDelete = useCallback((deleted: Node[]) => {
    if (!editable) return
    deleted.forEach((n) => deleteTicket(n.id))
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
    const currentNodes = useBoard.getState().nodes
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
          {useBoard.getState().presence.find((p) => p.userId === c.userId)?.username ?? '?'}
        </div>
      )),
    [cursors],
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
        onNodesChange={applyNodeChangesLocally}
        onEdgesChange={(changes) => {
          onEdgesDelete(changes)
          setEdges((eds) =>
            eds
              .map((e) => {
                const sel = changes.find((c) => 'id' in c && c.id === e.id && c.type === 'select')
                return sel ? { ...e, selected: (sel as { selected?: boolean }).selected } : e
              })
              .filter((e) => !changes.some((c) => 'id' in c && c.id === e.id && c.type === 'remove')),
          )
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
        </div>
      )}
      {cursorLabels}
      {shareOpen && <ShareModal boardId={id} onClose={() => setShareOpen(false)} />}
    </div>
  )
}
