import { useRef, useCallback } from 'react';
import { getCandidate } from '../lib/api';

// In-memory cache with TTL
const prefetchCache = new Map();
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

/**
 * Hook for prefetching candidate detail data on hover.
 *
 * Usage:
 * const { prefetchCandidate, getCachedCandidate } = usePrefetch();
 *
 * <div onMouseEnter={() => prefetchCandidate(candidate.id)}>
 *   ...
 * </div>
 *
 * // Later, when navigating to detail page:
 * const cached = getCachedCandidate(id);
 */
export function usePrefetch() {
  const hoverTimerRef = useRef(null);
  const inflightRef = useRef(new Set());  // prevent duplicate requests

  const prefetchCandidate = useCallback((candidateId) => {
    // 1. Clear any existing timer
    if (hoverTimerRef.current) {
      clearTimeout(hoverTimerRef.current);
      hoverTimerRef.current = null;
    }

    // 2. Set 200ms delay timer
    hoverTimerRef.current = setTimeout(async () => {
      // 3. Check if already cached (and not expired), skip if so
      const entry = prefetchCache.get(candidateId);
      if (entry && Date.now() - entry.timestamp <= CACHE_TTL) {
        return;
      }

      // 4. Check if already in-flight, skip if so
      if (inflightRef.current.has(candidateId)) {
        return;
      }

      // 5. Call API to fetch candidate detail
      inflightRef.current.add(candidateId);
      try {
        const data = await getCandidate(candidateId);
        // 6. Store result in prefetchCache with timestamp
        prefetchCache.set(candidateId, { data, timestamp: Date.now() });
      } catch (err) {
        // Silently fail on prefetch errors — the actual page will retry
        console.warn('Prefetch failed for candidate', candidateId, err);
      } finally {
        // 7. Remove from in-flight set
        inflightRef.current.delete(candidateId);
      }
    }, 200);
  }, []);

  const cancelPrefetch = useCallback(() => {
    // Clear the hover timer (for onMouseLeave)
    if (hoverTimerRef.current) {
      clearTimeout(hoverTimerRef.current);
      hoverTimerRef.current = null;
    }
  }, []);

  const getCachedCandidate = useCallback((candidateId) => {
    const entry = prefetchCache.get(candidateId);
    if (!entry) return null;
    if (Date.now() - entry.timestamp > CACHE_TTL) {
      prefetchCache.delete(candidateId);
      return null;
    }
    return entry.data;
  }, []);

  return { prefetchCandidate, cancelPrefetch, getCachedCandidate };
}
