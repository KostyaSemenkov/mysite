import { useEffect, useRef } from 'react'
import { Handle, Position, type NodeProps, type Node } from '@xyflow/react'
import { useBoard, updateTicket, STICKER_COLORS, type TicketData } from '../store'

export type TicketNodeType = Node<TicketData, 'ticket'>

export default function TicketNode({ id, data, selected }: NodeProps<TicketNodeType>) {
  const role = useBoard((s) => s.role)
  const editable = role === 'owner' || role === 'editor'
  const taRef = useRef<HTMLTextAreaElement | null>(null)

  // вход в режим редактирования — фокус в конец текста
  useEffect(() => {
    if (data.editing && taRef.current) {
      taRef.current.focus()
      const len = taRef.current.value.length
      taRef.current.setSelectionRange(len, len)
    }
  }, [data.editing])

  function commit(newText: string, oldText: string) {
    updateTicket(id, { text: newText, editing: false },
      newText !== oldText ? { text: oldText } : undefined)
  }

  return (
    <div
      className={`ticket-node${selected ? ' selected' : ''}`}
      style={{ ['--node-color' as string]: data.color }}
      onDoubleClick={() => editable && updateTicket(id, { editing: true })}
      title={editable ? 'Двойной клик — редактировать текст' : undefined}
    >
      {editable && <Handle type="source" position={Position.Right} />}
      {data.editing ? (
        <>
          <textarea
            ref={taRef}
            className="nodrag"
            defaultValue={data.text}
            spellCheck={false}
            placeholder="Текст…"
            maxLength={100}
            onChange={(e) => updateTicket(id, { text: e.target.value })}
            onBlur={(e) => commit(e.target.value, data.text)}
            onKeyDown={(e) => {
              if (e.key === 'Escape') commit(data.text, data.text)
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                commit((e.target as HTMLTextAreaElement).value, data.text)
              }
            }}
          />
          <span className="char-counter nodrag">{data.text.length}/100</span>
        </>
      ) : (
        <div className="ticket-text">{data.text || (editable ? '✏️ двойной клик' : '')}</div>
      )}
      {editable && (
        <div className="color-dots nodrag">
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
