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

  const completeBatchAnalysis = useCallback(() => {
    setAnalysisProgress((prev) => ({
      ...prev,
      isActive: false,
      completed: prev.total,
    }))
    completeTimeoutRef.current = setTimeout(() => {
      resetProgress()
    }, 3000)
  }, [])

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

  const value = {
    analysisProgress,
    notifications,
    startBatchAnalysis,
    updateProgress,
    completeBatchAnalysis,
    resetProgress,
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
