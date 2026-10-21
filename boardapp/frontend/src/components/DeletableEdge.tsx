import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  type Edge,
  type EdgeProps,
} from '@xyflow/react'
import { deleteEdgeWithSnapshot } from '../store'

export type DeletableEdgeType = Edge<{}, 'deletable'>

/**
 * Связь со зримым механизмом удаления: при наведении/выделении
 * в середине стрелки появляется кнопка ✕.
 */
export default function DeletableEdge({
  id, source, target, sourceX, sourceY, targetX, targetY,
  sourcePosition, targetPosition, markerEnd,
}: EdgeProps<DeletableEdgeType>) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition,
  })

  return (
    <>
      <BaseEdge id={id} path={edgePath} markerEnd={markerEnd} />
      <EdgeLabelRenderer>
        <button
          className="edge-delete nodrag nopan"
          title="Удалить связь"
          style={{
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            pointerEvents: 'all',
          }}
          onClick={(e) => {
            e.stopPropagation()
            deleteEdgeWithSnapshot({ id, source, target })
          }}
        >
          ×
        </button>
      </EdgeLabelRenderer>
    </>
  )
}
