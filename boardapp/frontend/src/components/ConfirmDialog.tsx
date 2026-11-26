import { useEffect, useRef } from 'react'

interface ConfirmDialogProps {
  title: string
  message: string
  confirmLabel?: string
  onConfirm: () => void
  onClose: () => void
}

/**
 * Подтверждение опасного действия вместо window.confirm(): модальный <dialog>,
 * фокус сразу на безопасной кнопке «Отмена», Esc и клик по фону закрывают.
 * О закрытии сообщаем родителю из каждого пути: браузер не гарантирует
 * событие close для закрытия по запросу (см. также ShareModal).
 */
export default function ConfirmDialog({
  title, message, confirmLabel = 'Подтвердить', onConfirm, onClose,
}: ConfirmDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (!dialog.open) dialog.showModal()
    const onPointerDown = (e: PointerEvent) => { if (e.target === dialog) onClose() }
    document.addEventListener('pointerdown', onPointerDown, true)
    return () => document.removeEventListener('pointerdown', onPointerDown, true)
  }, [onClose])

  return (
    <dialog
      ref={dialogRef}
      className="confirm-dialog"
      aria-labelledby="confirm-title"
      aria-describedby="confirm-message"
      closedby="any"
      onCancel={(event) => {
        // Esc: закрываем сами, а не снимаем окно прямо в обработчике — иначе браузер
        // не успевает вернуть фокус на элемент, который окно открыл
        event.preventDefault()
        dialogRef.current?.close()
        onClose()
      }}
      onClose={onClose}
    >
      <div className="confirm-panel">
        <h2 id="confirm-title">{title}</h2>
        <p id="confirm-message">{message}</p>
        <div className="confirm-actions">
          <button type="button" className="btn ghost" onClick={onClose}>Отмена</button>
          <button type="button" className="btn danger" onClick={() => { onClose(); onConfirm() }}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </dialog>
  )
}
