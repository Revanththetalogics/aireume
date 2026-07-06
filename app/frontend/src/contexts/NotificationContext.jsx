import { createContext, useContext, useState, useCallback, useRef } from 'react'

export const NotificationContext = createContext(null)

export function NotificationProvider({ children }) {
  const [analysisProgress, setAnalysisProgress] = useState({
    isActive: false,
    completed: 0,
    total: 0,
    items: [],
  })
  const [notifications, setNotifications] = useState([])
  const completeTimeoutRef = useRef(null)

  const startBatchAnalysis = useCallback((total) => {
    if (completeTimeoutRef.current) {
      clearTimeout(completeTimeoutRef.current)
      completeTimeoutRef.current = null
    }
    setAnalysisProgress({
      isActive: true,
      completed: 0,
      total,
      items: [],
    })
  }, [])

  const updateProgress = useCallback((filename, status) => {
    setAnalysisProgress((prev) => {
      const existingIndex = prev.items.findIndex((item) => item.filename === filename)
      let newItems
      if (existingIndex >= 0) {
        newItems = prev.items.map((item, idx) =>
          idx === existingIndex ? { ...item, status } : item
        )
      } else {
        newItems = [...prev.items, { filename, status }]
      }

      const completedCount = newItems.filter(
        (item) => item.status === 'completed' || item.status === 'error'
      ).length

      return {
        ...prev,
        completed: completedCount,
        items: newItems,
      }
    })
  }, [])

  const addNotification = useCallback((notification) => {
    const id = notification.id || `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    setNotifications((prev) => [
      {
        id,
        type: notification.type || 'info', // info | success | warning | error
        title: notification.title || '',
        message: notification.message || '',
        href: notification.href || null,
        read: false,
        createdAt: new Date().toISOString(),
      },
      ...prev,
    ].slice(0, 50)) // cap history
    return id
  }, [])

  const markNotificationRead = useCallback((id) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    )
  }, [])

  const markAllNotificationsRead = useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))
  }, [])

  const removeNotification = useCallback((id) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id))
  }, [])

  const clearNotifications = useCallback(() => setNotifications([]), [])

  const completeBatchAnalysis = useCallback(() => {
    setAnalysisProgress((prev) => {
      const errors = prev.items.filter((i) => i.status === 'error').length
      const succeeded = prev.total - errors
      addNotification({
        type: errors > 0 ? 'warning' : 'success',
        title: 'Batch analysis complete',
        message:
          errors > 0
            ? `${succeeded} of ${prev.total} resumes analyzed (${errors} failed).`
            : `All ${prev.total} resumes analyzed successfully.`,
        href: '/candidates',
      })
      return { ...prev, isActive: false, completed: prev.total }
    })
    completeTimeoutRef.current = setTimeout(() => {
      resetProgress()
    }, 3000)
  }, [addNotification])

  const resetProgress = useCallback(() => {
    if (completeTimeoutRef.current) {
      clearTimeout(completeTimeoutRef.current)
      completeTimeoutRef.current = null
    }
    setAnalysisProgress({
      isActive: false,
      completed: 0,
      total: 0,
      items: [],
    })
  }, [])

  const unreadCount = notifications.filter((n) => !n.read).length

  const value = {
    analysisProgress,
    notifications,
    unreadCount,
    startBatchAnalysis,
    updateProgress,
    completeBatchAnalysis,
    resetProgress,
    addNotification,
    markNotificationRead,
    markAllNotificationsRead,
    removeNotification,
    clearNotifications,
  }

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  )
}

export function useNotification() {
  const ctx = useContext(NotificationContext)
  if (!ctx) throw new Error('useNotification must be used within NotificationProvider')
  return ctx
}
