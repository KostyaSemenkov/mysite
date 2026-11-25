import { useState } from 'react'
import { NodeResizer, type Node, type NodeProps } from '@xyflow/react'
import { updateZone, useBoard, requestDeleteNode, ZONE_COLORS } from '../store'
import type { ZoneData } from '../boardEvents'

export type ZoneNodeType = Node<ZoneData, 'zone'>

export default function ZoneNode({ id, data, selected }: NodeProps<ZoneNodeType>) {
  const role = useBoard((s) => s.role)
  const editable = role === 'owner' || role === 'editor'
  const [editing, setEditing] = useState(false)

  function rename(raw: string) {
    updateZone(id, { title: raw.trim() || 'Группа' })
    setEditing(false)
  }

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
              updateZone(id, { x: params.x, y: params.y, width: params.width, height: params.height })
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
          aria-label="Название группы"
          placeholder="Название группы"
          onBlur={(e) => rename(e.target.value)}
          onKeyDown={(e) => {
            // Enter при наборе раскладкой IME подтверждает ввод, а не название
            if (e.nativeEvent.isComposing || e.keyCode === 229) {
              e.preventDefault()
              return
            }
            if (e.key === 'Enter') rename((e.target as HTMLInputElement).value)
            if (e.key === 'Escape') setEditing(false)
          }}
        />
      ) : (
        <div
          className="zone-title nodrag nowheel"
          tabIndex={editable ? 0 : undefined}
          role={editable ? 'button' : undefined}
          aria-label={editable ? `Переименовать группу «${data.title || 'Группа'}»` : undefined}
          onDoubleClick={() => editable && setEditing(true)}
          onKeyDown={(e) => {
            if (!editable || e.key !== 'Enter') return
            e.preventDefault()
            setEditing(true)
          }}
          title={editable ? 'Двойной клик или Enter — переименовать' : undefined}
        >
          {data.title || 'Группа'}
        </div>
      )}
      {editable && !editing && (
        <div className="zone-tools nodrag">
          <button
            type="button"
            className="node-delete nodrag"
            title="Удалить группу"
            aria-label="Удалить группу"
            onClick={(e) => {
              e.stopPropagation()
              requestDeleteNode(id)
            }}
          >×</button>
          {ZONE_COLORS.map((c, index) => (
            <button
              key={c}
              type="button"
              className="zone-color-dot"
              style={{ background: c }}
              title={`Цвет группы ${index + 1}`}
              aria-label={`Цвет группы ${index + 1}`}
              aria-pressed={(data.color || ZONE_COLORS[0]) === c}
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
