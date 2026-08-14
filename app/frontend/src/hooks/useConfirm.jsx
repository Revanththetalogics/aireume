import { useCallback, useState } from 'react'
import ConfirmDialog from '../components/ConfirmDialog'

export default function useConfirm() {
  const [state, setState] = useState({
    open: false,
    title: '',
    message: '',
    confirmLabel: 'Confirm',
    danger: false,
    resolve: null,
  })

  const confirm = useCallback((opts) => {
    const options = typeof opts === 'string' ? { message: opts } : (opts || {})
    return new Promise((resolve) => {
      setState({
        open: true,
        title: options.title || 'Please confirm',
        message: options.message || '',
        confirmLabel: options.confirmLabel || 'Confirm',
        danger: Boolean(options.danger),
        resolve,
      })
    })
  }, [])

  const close = (value) => {
    state.resolve?.(value)
    setState((prev) => ({ ...prev, open: false, resolve: null }))
  }

  const dialog = (
    <ConfirmDialog
      open={state.open}
      title={state.title}
      message={state.message}
      confirmLabel={state.confirmLabel}
      danger={state.danger}
      onConfirm={() => close(true)}
      onCancel={() => close(false)}
    />
  )

  return { confirm, dialog }
}
