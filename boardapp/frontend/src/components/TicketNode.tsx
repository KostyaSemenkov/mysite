import { Handle, Position, type NodeProps, type Node } from '@xyflow/react'
import { useBoard, updateTicket, STICKER_COLORS, type TicketData } from '../store'

export type TicketNodeType = Node<TicketData, 'ticket'>

export default function TicketNode({ id, data, selected }: NodeProps<TicketNodeType>) {
  const role = useBoard((s) => s.role)
  const editable = role === 'owner' || role === 'editor'

  return (
    <div
      className={`ticket-node${selected ? ' selected' : ''}`}
      style={{ ['--node-color' as string]: data.color }}
      onDoubleClick={() => editable && updateTicket(id, { text: data.text })}
    >
      {editable && <Handle type="source" position={Position.Right} />}
      <textarea
        value={data.text}
        readOnly={!editable}
        placeholder="Текст…"
        spellCheck={false}
        onChange={(e) => updateTicket(id, { text: e.target.value })}
        onBlur={(e) => {
          // финальный текст — с undo-точкой
          if (editable && e.target.value !== data.text) return
        }}
      />
      {editable && (
        <div className="color-dots">
          {STICKER_COLORS.map((c) => (
            <span
              key={c}
              className="color-dot"
              style={{ background: c }}
              onClick={(e) => {
                e.stopPropagation()
                updateTicket(id, { color: c }, { color: data.color })
              }}
            />
          ))}
        </div>
      )}
      {editable && <Handle type="target" position={Position.Left} />}
    </div>
  )
}
