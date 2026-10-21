import { useState } from 'react'
import { NodeResizer, type Node, type NodeProps } from '@xyflow/react'
import { updateZone, useBoard, ZONE_COLORS } from '../store'
import type { ZoneData } from '../boardEvents'

export type ZoneNodeType = Node<ZoneData, 'zone'>

export default function ZoneNode({ id, data, selected }: NodeProps<ZoneNodeType>) {
  const role = useBoard((s) => s.role)
  const editable = role === 'owner' || role === 'editor'
  const [editing, setEditing] = useState(false)

  return (
    <div
      className={`zone-node${selected ? ' selected' : ''}`}
      style={{ ['--zone-color' as string]: data.color || ZONE_COLORS[0] }}
    >
      {editable && (
        <NodeResizer
          isVisible={selected}
          minWidth={240}
          minHeight={140}
          lineClassName="zone-resize-line"
          handleClassName="zone-resize-handle"
          onResizeEnd={(_, params) => {
            if (params.width && params.height) {
              updateZone(id, { width: params.width, height: params.height })
            }
          }}
        />
      )}
      {editing ? (
        <input
          className="zone-title-input nodrag"
          defaultValue={data.title}
          autoFocus
          maxLength={60}
          placeholder="Название зоны"
          onBlur={(e) => {
            updateZone(id, { title: e.target.value.trim() || 'Зона' })
            setEditing(false)
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              const v = (e.target as HTMLInputElement).value.trim() || 'Зона'
              updateZone(id, { title: v })
              setEditing(false)
            }
            if (e.key === 'Escape') setEditing(false)
          }}
        />
      ) : (
        <div
          className="zone-title nodrag nowheel"
          onDoubleClick={() => editable && setEditing(true)}
          title={editable ? 'Двойной клик — переименовать' : undefined}
        >
          {data.title || 'Зона'}
        </div>
      )}
      {editable && !editing && (
        <div className="zone-color-dots nodrag">
          {ZONE_COLORS.map((c) => (
            <span
              key={c}
              className="zone-color-dot"
              style={{ background: c }}
              title="Цвет зоны"
              onClick={(e) => {
                e.stopPropagation()
                updateZone(id, { color: c }, { color: data.color || ZONE_COLORS[0] })
              }}
            />
          ))}
        </div>
      )}
    </div>
  )
}
