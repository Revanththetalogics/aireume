import toast from 'react-hot-toast'

// Errors persist longer than successes so users have time to read them.
export const showSuccess = (message) => toast.success(message, { duration: 3000 })

export const showError = (message) => toast.error(message, { duration: 6000 })

export const showUndo = (message, onUndo, duration = 5000) => {
  return toast.custom(
    (t) => (
      <div
        className={`${
          t.visible ? 'animate-fade-up' : ''
        } flex items-center gap-3 bg-white rounded-xl px-4 py-3 shadow-brand border border-brand-100`}
        style={{
          fontFamily: "'Inter', system-ui, sans-serif",
          fontSize: '0.875rem',
          fontWeight: 500,
          color: '#1e293b',
          minWidth: '280px',
        }}
      >
        <span className="flex-1">{message}</span>
        <button
          onClick={() => {
            onUndo()
            toast.dismiss(t.id)
          }}
          className="text-brand-600 hover:text-brand-700 font-semibold text-sm px-2 py-1 rounded-md hover:bg-brand-50 transition-colors"
        >
          Undo
        </button>
      </div>
    ),
    { duration }
  )
}

export const showLoading = (message) => toast.loading(message, { duration: Infinity })

export const dismissToast = (id) => toast.dismiss(id)