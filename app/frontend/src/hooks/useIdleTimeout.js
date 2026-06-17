import { useRef, useEffect, useCallback, useState } from 'react'

const IDLE_TIMEOUT_MS = 30 * 60 * 1000  // 30 minutes
const WARNING_DURATION_MS = 60 * 1000     // 60-second countdown
const ACTIVITY_THROTTLE_MS = 30 * 1000    // throttle activity updates to every 30s
const CHECK_INTERVAL_MS = 30 * 1000       // how often to check idle during normal phase
const STORAGE_KEY = 'aria_last_activity'

const ACTIVITY_EVENTS = ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll']

/**
 * Hook to detect user inactivity and trigger a warning + auto-logout.
 *
 * @param {boolean} isActive - Only run when the user is authenticated
 * @param {function} onTimeout - Called when the full idle + warning period elapses
 * @returns {{ isWarning: boolean, countdown: number, resetTimer: function }}
 */
export default function useIdleTimeout(isActive, onTimeout) {
  const [isWarning, setIsWarning] = useState(false)
  const [countdown, setCountdown] = useState(0)

  const lastActivityRef = useRef(Date.now())
  const checkIntervalRef = useRef(null)
  const countdownIntervalRef = useRef(null)
  const warningStartRef = useRef(null)
  const onTimeoutRef = useRef(onTimeout)

  // Keep the callback ref current without re-attaching listeners
  useEffect(() => {
    onTimeoutRef.current = onTimeout
  }, [onTimeout])

  // Write current timestamp to localStorage for cross-tab sync
  const syncActivity = useCallback(() => {
    try {
      localStorage.setItem(STORAGE_KEY, String(Date.now()))
    } catch { /* ignore storage errors */ }
  }, [])

  // Read the latest activity timestamp (local or from another tab)
  const getLastActivity = useCallback(() => {
    try {
      const stored = Number(localStorage.getItem(STORAGE_KEY))
      if (stored && stored > lastActivityRef.current) {
        lastActivityRef.current = stored
      }
    } catch { /* ignore */ }
    return lastActivityRef.current
  }, [])

  // ── Activity detection (throttled) ────────────────────────────────
  const lastThrottleRef = useRef(0)

  const handleActivity = useCallback(() => {
    const now = Date.now()
    if (now - lastThrottleRef.current < ACTIVITY_THROTTLE_MS) return
    lastThrottleRef.current = now

    lastActivityRef.current = now
    syncActivity()

    // If we're in the warning phase, dismiss it immediately
    if (warningStartRef.current !== null) {
      warningStartRef.current = null
      setIsWarning(false)
      setCountdown(0)
      if (countdownIntervalRef.current) {
        clearInterval(countdownIntervalRef.current)
        countdownIntervalRef.current = null
      }
    }
  }, [syncActivity])

  // ── Warning + countdown phase ─────────────────────────────────────
  const startWarning = useCallback(() => {
    warningStartRef.current = Date.now()
    setIsWarning(true)
    setCountdown(Math.ceil(WARNING_DURATION_MS / 1000))

    countdownIntervalRef.current = setInterval(() => {
      const elapsed = Date.now() - (warningStartRef.current || Date.now())
      const remaining = Math.ceil((WARNING_DURATION_MS - elapsed) / 1000)

      if (remaining <= 0) {
        clearInterval(countdownIntervalRef.current)
        countdownIntervalRef.current = null
        setIsWarning(false)
        setCountdown(0)
        warningStartRef.current = null
        onTimeoutRef.current()
      } else {
        setCountdown(remaining)
      }
    }, 1000)
  }, [])

  // ── Normal idle check phase ───────────────────────────────────────
  const startIdleCheck = useCallback(() => {
    checkIntervalRef.current = setInterval(() => {
      const lastActivity = getLastActivity()
      const idleDuration = Date.now() - lastActivity

      if (idleDuration >= IDLE_TIMEOUT_MS && warningStartRef.current === null) {
        startWarning()
      }
    }, CHECK_INTERVAL_MS)
  }, [getLastActivity, startWarning])

  // ── Reset timer (exposed for "Stay Logged In") ────────────────────
  const resetTimer = useCallback(() => {
    const now = Date.now()
    lastActivityRef.current = now
    lastThrottleRef.current = now
    warningStartRef.current = null
    syncActivity()

    setIsWarning(false)
    setCountdown(0)

    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current)
      countdownIntervalRef.current = null
    }
  }, [syncActivity])

  // ── Main lifecycle ────────────────────────────────────────────────
  useEffect(() => {
    if (!isActive) {
      // Not authenticated — clean everything up
      if (checkIntervalRef.current) clearInterval(checkIntervalRef.current)
      if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current)
      checkIntervalRef.current = null
      countdownIntervalRef.current = null
      warningStartRef.current = null
      setIsWarning(false)
      setCountdown(0)
      return
    }

    // Initialise activity timestamp
    lastActivityRef.current = Date.now()
    syncActivity()

    // Attach DOM activity listeners
    ACTIVITY_EVENTS.forEach(event =>
      window.addEventListener(event, handleActivity, { passive: true })
    )

    // Start the periodic idle check
    startIdleCheck()

    // Listen for storage events from other tabs
    const handleStorage = (e) => {
      if (e.key === STORAGE_KEY && e.newValue) {
        const remoteTs = Number(e.newValue)
        if (remoteTs > lastActivityRef.current) {
          lastActivityRef.current = remoteTs

          // If another tab's activity arrives while we're warning, dismiss
          if (warningStartRef.current !== null) {
            warningStartRef.current = null
            setIsWarning(false)
            setCountdown(0)
            if (countdownIntervalRef.current) {
              clearInterval(countdownIntervalRef.current)
              countdownIntervalRef.current = null
            }
          }
        }
      }
    }
    window.addEventListener('storage', handleStorage)

    return () => {
      ACTIVITY_EVENTS.forEach(event =>
        window.removeEventListener(event, handleActivity)
      )
      window.removeEventListener('storage', handleStorage)
      if (checkIntervalRef.current) clearInterval(checkIntervalRef.current)
      if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current)
      checkIntervalRef.current = null
      countdownIntervalRef.current = null
      warningStartRef.current = null
    }
  }, [isActive, handleActivity, syncActivity, startIdleCheck])

  return { isWarning, countdown, resetTimer }
}
