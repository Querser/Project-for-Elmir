import Button from './Button.jsx';

export default function ConfirmDialog({
  open,
  title,
  description,
  confirmText = 'Подтвердить',
  cancelText = 'Отмена',
  confirmVariant = 'danger',
  onConfirm,
  onClose,
  busy = false,
}) {
  if (!open) return null;

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true">
      <div className="modal-sheet">
        <div className="modal-title">{title}</div>
        {description ? <div className="modal-desc">{description}</div> : null}

        <div className="modal-actions">
          <Button variant="ghost" onClick={onClose} disabled={busy}>
            {cancelText}
          </Button>
          <Button variant={confirmVariant} onClick={onConfirm} disabled={busy}>
            {confirmText}
          </Button>
        </div>
      </div>
    </div>
  );
}
