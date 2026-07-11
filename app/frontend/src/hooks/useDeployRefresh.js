import { useEffect, useRef } from 'react'
import { showError } from '../lib/toast'

const BUILD_ID = typeof __APP_BUILD_ID__ !== 'undefined' ? __APP_BUILD_ID__ : 'dev'

/**
 * After deploy, cached index.html may reference missing chunks.
 * Poll /api/version and prompt refresh when build_id changes.
 */
export default function useDeployRefresh() {
  const initialBuild = useRef(BUILD_ID)
  const prompted = useRef(false)

  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch('/api/version', { credentials: 'include' })
        if (!res.ok) return
        const data = await res.json()
        const remote = data.build_id
        if (
          remote &&
          initialBuild.current !== 'dev' &&
          remote !== initialBuild.current &&
          !prompted.current
        ) {
          prompted.current = true
          showError('A new version is available. Please refresh the page.')
        }
      } catch {
        /* ignore */
      }
    }
    check()
    const id = setInterval(check, 5 * 60 * 1000)
    return () => clearInterval(id)
  }, [])
}
