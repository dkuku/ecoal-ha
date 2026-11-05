<script>
  let {
    open = false,
    title = 'Potwierdzenie operacji',
    message = 'Czy na pewno chcesz wykonać tę operację?',
    confirmText = 'Potwierdź',
    cancelText = 'Anuluj',
    danger = true,
    icon = '⚠️',
    onConfirm = () => {},
    onCancel = () => {},
  } = $props();

  function handleKeydown(e) {
    if (e.key === 'Escape' && open) {
      onCancel();
    }
  }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
  <div class="modal-backdrop" onclick={onCancel} role="presentation">
    <div
      class="modal-card"
      class:danger
      onclick={(e) => e.stopPropagation()}
      onkeydown={(e) => e.stopPropagation()}
      role="dialog"
      aria-modal="true"
      tabindex="-1"
    >
      <div class="modal-header">
        <span class="modal-icon">{icon}</span>
        <h3 class="modal-title">{title}</h3>
      </div>

      <div class="modal-body">
        <p class="modal-message">{message}</p>
      </div>

      <div class="modal-actions">
        <button type="button" class="btn-modal-cancel" onclick={onCancel}>
          {cancelText}
        </button>
        <button
          type="button"
          class="btn-modal-confirm"
          class:btn-danger={danger}
          onclick={onConfirm}
        >
          {confirmText}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(10, 15, 29, 0.75);
    backdrop-filter: blur(6px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
    padding: 1rem;
    animation: fadeIn 0.15s ease-out;
  }

  .modal-card {
    background: #1e293b;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 14px;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255, 255, 255, 0.05);
    max-width: 460px;
    width: 100%;
    padding: 1.5rem;
    transform: translateY(0);
    animation: slideUp 0.18s ease-out;
  }

  .modal-card.danger {
    border-color: rgba(239, 68, 68, 0.45);
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6), 0 0 20px rgba(239, 68, 68, 0.15);
  }

  .modal-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.85rem;
  }

  .modal-icon {
    font-size: 1.6rem;
    line-height: 1;
  }

  .modal-title {
    margin: 0;
    font-size: 1.15rem;
    font-weight: 700;
    color: #f8fafc;
  }

  .modal-body {
    margin-bottom: 1.4rem;
  }

  .modal-message {
    margin: 0;
    font-size: 0.92rem;
    line-height: 1.5;
    color: #cbd5e1;
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
  }

  .btn-modal-cancel {
    background: rgba(255, 255, 255, 0.08);
    color: #cbd5e1;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    padding: 0.55rem 1.1rem;
    font-size: 0.88rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .btn-modal-cancel:hover {
    background: rgba(255, 255, 255, 0.15);
    color: #ffffff;
  }

  .btn-modal-confirm {
    background: #3b82f6;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 0.55rem 1.25rem;
    font-size: 0.88rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .btn-modal-confirm:hover {
    background: #2563eb;
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.35);
  }

  .btn-modal-confirm.btn-danger {
    background: #dc2626;
  }

  .btn-modal-confirm.btn-danger:hover {
    background: #b91c1c;
    box-shadow: 0 4px 12px rgba(220, 38, 38, 0.4);
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @keyframes slideUp {
    from { transform: translateY(12px) scale(0.98); opacity: 0; }
    to { transform: translateY(0) scale(1); opacity: 1; }
  }
</style>
