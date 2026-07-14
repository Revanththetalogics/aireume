import { useState, useCallback, useRef } from 'react'
import AnalyticsShell from '../components/patterns/AnalyticsShell'

export default function AnalyticsLayout() {
  const [refreshing, setRefreshing] = useState(false)
  const [generatedAt, setGeneratedAt] = useState(null)
  const [hasRefresh, setHasRefresh] = useState(false)
  const refreshRef = useRef(null)

  const registerRefresh = useCallback((fn) => {
    refreshRef.current = fn
    setHasRefresh(Boolean(fn))
  }, [])

  const handleRefresh = async () => {
    if (!refreshRef.current) return
    setRefreshing(true)
    try {
      await refreshRef.current()
    } finally {
      setRefreshing(false)
    }
  }

  return (
    <AnalyticsShell
      onRefresh={hasRefresh ? handleRefresh : null}
      refreshing={refreshing}
      generatedAt={generatedAt}
      outletContext={{ registerRefresh, setGeneratedAt }}
    />
  )
}
