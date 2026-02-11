import Card from './Card.jsx';
import Button from './Button.jsx';

/**
 * Простая модалка без порталов.
 * Закрытие: по клику в затемнение или по кнопке.
 */
export default function Modal({ title, children, onClose, actions }) {
  return (
    <div
      className="modal-backdrop"
      onMouseDown={() => onClose?.()}
      role="dialog"
      aria-modal="true"
    >
      <div className="modal" onMouseDown={(e) => e.stopPropagation()}>
        <Card className="modal-card">
          {title ? <div className="modal-title">{title}</div> : null}
          <div className="modal-body">{children}</div>

          <div className="modal-actions">
            {actions ? (
              actions
            ) : (
              <Button variant="secondary" onClick={() => onClose?.()}>
                Закрыть
              </Button>
            )}
          </div>
        </Card>
      </div>

      {/* Fallback-стили, если вдруг у тебя нет CSS под modal-* */}
      <style>{`
        .modal-backdrop {
          position: fixed;
          inset: 0;
          background: rgba(15, 23, 42, 0.35);
          display: grid;
          place-items: center;
          padding: 18px;
          z-index: 9998;
        }
        .modal {
          width: 520px;
          max-width: calc(100vw - 36px);
        }
        .modal-card {
          padding: 16px;
        }
        .modal-title {
          font-weight: 900;
          font-size: 18px;
        }
        .modal-body {
          margin-top: 10px;
        }
        .modal-actions {
          margin-top: 14px;
          display: flex;
          gap: 10px;
          justify-content: flex-end;
          flex-wrap: wrap;
        }
      `}</style>
    </div>
  );
}

/**
 * ConfirmModal — то, что использует Trainings.jsx
 */
export function ConfirmModal({
  title = 'Подтвердите',
  text,
  onCancel,
  onConfirm,
  confirmText = 'Подтвердить',
  cancelText = 'Назад',
}) {
  return (
    <Modal
      title={title}
      onClose={onCancel}
      actions={
        <>
          <Button variant="secondary" onClick={onCancel}>
            {cancelText}
          </Button>
          <Button variant="danger" onClick={onConfirm}>
            {confirmText}
          </Button>
        </>
      }
    >
      <div className="muted">{text}</div>
    </Modal>
  );
}
