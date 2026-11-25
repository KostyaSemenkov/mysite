import { useEffect, useRef } from 'react'
import { Handle, Position, type NodeProps, type Node } from '@xyflow/react'
import { useBoard, updateTicket, requestDeleteNode, STICKER_COLORS, type TicketData } from '../store'

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
      title={editable ? 'Двойной клик или Enter — редактировать текст' : undefined}
    >
      <Handle type="source" position={Position.Right} isConnectable={editable}
        style={{ visibility: editable ? 'visible' : 'hidden' }} />
      {data.editing ? (
        <>
          <textarea
            ref={taRef}
            className="nodrag"
            defaultValue={data.text}
            spellCheck={false}
            aria-label="Текст тикета"
            placeholder="Текст…"
            maxLength={100}
            onChange={(e) => updateTicket(id, { text: e.target.value })}
            onBlur={(e) => commit(e.target.value, data.text)}
            onKeyDown={(e) => {
              // Enter при наборе раскладкой IME (китайский, японский) подтверждает
              // ввод иероглифа, а не заканчивает правку
              if (e.nativeEvent.isComposing || e.keyCode === 229) {
                e.preventDefault()
                return
              }
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
        <div
          className="ticket-text"
          // с клавиатуры в редактирование — Enter или F2 (двойной клик — не для всех)
          tabIndex={editable ? 0 : undefined}
          role={editable ? 'button' : undefined}
          aria-label={editable ? `Редактировать тикет: ${data.text || 'пустой'}` : undefined}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === 'F2') {
              e.preventDefault()
              updateTicket(id, { editing: true })
            }
          }}
        >{data.text || (editable ? '✏️ двойной клик' : '')}</div>
      )}
      {editable && (
        <button
          type="button"
          className="node-delete nodrag"
          title="Удалить тикет"
          aria-label="Удалить тикет"
          onClick={(e) => {
            e.stopPropagation()
            requestDeleteNode(id)
          }}
        >×</button>
      )}
      {editable && (
        <div className="color-dots nodrag">
          {STICKER_COLORS.map((c, index) => (
            <button
              key={c}
              type="button"
              className="color-dot"
              style={{ background: c }}
              title={`Цвет ${index + 1}`}
              aria-label={`Цвет ${index + 1}`}
              aria-pressed={data.color === c}
              onClick={(e) => {
                e.stopPropagation()
                updateTicket(id, { color: c }, { color: data.color })
              }}
            />
          ))}
        </div>
      )}
      <Handle type="target" position={Position.Left} isConnectable={editable}
        style={{ visibility: editable ? 'visible' : 'hidden' }} />
    </div>
  )
}
