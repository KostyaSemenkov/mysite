import { useState } from 'react'
import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  type Edge,
  type EdgeProps,
} from '@xyflow/react'
import type { EdgeData } from '../boardEvents'
import { commitBatch, useBoard } from '../store'

export type DeletableEdgeType = Edge<EdgeData, 'deletable'>

export default function DeletableEdge({
  id, source, target, sourceX, sourceY, targetX, targetY,
  sourcePosition, targetPosition, markerEnd, selected, data,
}: EdgeProps<DeletableEdgeType>) {
  const editable = useBoard((s) => s.role === 'owner' || s.role === 'editor')
  const [draft, setDraft] = useState<string | null>(null)
  const label = data?.label ?? ''
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition,
  })

  function saveLabel(event: React.FormEvent) {
    event.preventDefault()
    if (draft === null || !editable) return
    const next = draft.trim()
    if (next !== label) {
      commitBatch(
        [{ type: 'edge:update', data: { id, label: next } }],
        [{ type: 'edge:update', data: { id, label } }],
      )
    }
    setDraft(null)
  }

  return (
    <>
      <BaseEdge id={id} path={edgePath} markerEnd={markerEnd} />
      <EdgeLabelRenderer>
        <div
          className="board-edge-label nodrag nopan"
          data-edge-id={id}
          style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}
        >
          {editable && draft !== null ? (
            <form className="edge-label-edit" onSubmit={saveLabel}
              onBlur={(e) => { if (!e.currentTarget.contains(e.relatedTarget)) setDraft(null) }}
              onKeyDown={(e) => { if (e.key === 'Escape') setDraft(null) }}>
              <input autoFocus aria-label="Подпись стрелки" value={draft} maxLength={100}
                onChange={(e) => setDraft(e.target.value)} />
              <button type="submit" title="Сохранить подпись" aria-label="Сохранить подпись">✓</button>
            </form>
          ) : (
            <>
              {label && <span className="edge-label-text"
                onDoubleClick={() => { if (editable) setDraft(label) }}>{label}</span>}
              {editable && selected && (
                <div className="edge-label-tools">
                  <button type="button" title="Подписать стрелку" aria-label="Подписать стрелку"
                    onClick={() => setDraft(label)}>✎</button>
                  <button type="button" title="Удалить связь" aria-label="Удалить связь"
                    onClick={() => commitBatch(
                      [{ type: 'edge:delete', data: { id } }],
                      [{ type: 'edge:create', data: { id, source, target, label } }],
                    )}>×</button>
                </div>
              )}
            </>
          )}
        </div>
      </EdgeLabelRenderer>
    </>
  )
}
