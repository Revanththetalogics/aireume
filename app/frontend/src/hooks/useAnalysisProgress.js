import { useContext } from 'react'
import { NotificationContext } from '../contexts/NotificationContext'

export function useAnalysisProgress() {
  const {
    analysisProgress,
    startBatchAnalysis,
    updateProgress,
    completeBatchAnalysis,
    resetProgress,
  } = useContext(NotificationContext)

  if (!analysisProgress) {
    throw new Error('useAnalysisProgress must be used within NotificationProvider')
  }

  return {
    ...analysisProgress,
    startBatchAnalysis,
    updateProgress,
    completeBatchAnalysis,
    resetProgress,
  }
}
