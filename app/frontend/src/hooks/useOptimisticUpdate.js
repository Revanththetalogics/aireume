import { useCallback } from 'react'
import { showError, showUndo } from '../lib/toast'

/**
 * Hook for optimistic UI updates with rollback on failure and undo support.
 *
 * @returns {Object} { optimisticUpdate }
 *
 * Usage:
 * const { optimisticUpdate } = useOptimisticUpdate();
 *
 * optimisticUpdate({
 *   items,                    // current state array
 *   setItems,                 // state setter
 *   itemId,                   // ID of item being updated
 *   idField: 'id',            // field or fn to match items (default: 'id')
 *   field: 'status',          // field to update on the matched item
 *   newValue: 'shortlisted',  // new value
 *   apiCall: () => updateResultStatus(itemId, 'shortlisted'),
 *   undoApiCall: () => updateResultStatus(itemId, previousValue), // optional
 *   undoMessage: 'Candidate shortlisted',
 * });
 */
export function useOptimisticUpdate() {
  const optimisticUpdate = useCallback(async ({
    items,
    setItems,
    itemId,
    idField = 'id',
    field,
    newValue,
    apiCall,
    undoApiCall,
    undoMessage,
  }) => {
    // Build a match function from idField (string field name or custom function)
    const matchFn = typeof idField === 'function'
      ? idField
      : (item) => item[idField]

    // 1. Find the item and save previous value for rollback
    const item = items.find(item => matchFn(item) === itemId)
    if (!item) return

    const previousValue = item[field]

    // Skip if value hasn't actually changed
    if (previousValue === newValue) return

    // 2. Immediately update UI (optimistic)
    setItems(prev => prev.map(item => {
      const isMatch = matchFn(item) === itemId
      return isMatch ? { ...item, [field]: newValue } : item
    }))

    // 3. Show undo toast with callback to rollback state AND call undo API
    showUndo(undoMessage, () => {
      // Rollback state to previous value
      setItems(prev => prev.map(item => {
        const isMatch = matchFn(item) === itemId
        return isMatch ? { ...item, [field]: previousValue } : item
      }))
      // Revert on server side if undoApiCall is provided
      if (undoApiCall) undoApiCall()
    })

    // 4. Call API in background
    try {
      await apiCall()
    } catch {
      // 5. On API failure: rollback state, show error toast
      setItems(prev => prev.map(item => {
        const isMatch = matchFn(item) === itemId
        return isMatch ? { ...item, [field]: previousValue } : item
      }))
      showError('Failed to update status. Change reverted.')
    }
  }, [])

  return { optimisticUpdate }
}