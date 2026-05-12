import { useEffect, useCallback } from 'react';

/**
 * Hook for keyboard shortcuts in candidate lists.
 *
 * @param {Object} options
 * @param {Array} options.items - Array of items to navigate
 * @param {number} options.selectedIndex - Currently selected index
 * @param {function} options.onSelect - Called with new index when J/K pressed
 * @param {function} options.onShortlist - Called when S pressed on selected item
 * @param {function} options.onReject - Called when R pressed on selected item
 * @param {function} options.onOpen - Called when Enter pressed on selected item
 * @param {function} [options.onSearch] - Called when Cmd/Ctrl+K pressed
 * @param {boolean} options.enabled - Whether shortcuts are active (default true)
 */
export function useKeyboardShortcuts({
  items,
  selectedIndex,
  onSelect,
  onShortlist,
  onReject,
  onOpen,
  onSearch,
  enabled = true,
}) {
  const handleKeyDown = useCallback(
    (e) => {
      if (!enabled || !items || items.length === 0) return;

      // Ignore events when user is typing in input, textarea, select, or contenteditable
      const tag = e.target.tagName;
      if (
        tag === 'INPUT' ||
        tag === 'TEXTAREA' ||
        tag === 'SELECT' ||
        e.target.isContentEditable
      ) {
        return;
      }

      const key = e.key;

      // Cmd+K / Ctrl+K: focus search
      if (key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        onSearch?.();
        return;
      }

      // J: select next candidate
      if (key === 'j') {
        e.preventDefault();
        onSelect(Math.min(selectedIndex + 1, items.length - 1));
        return;
      }

      // K: select previous candidate
      if (key === 'k') {
        e.preventDefault();
        onSelect(Math.max(selectedIndex - 1, 0));
        return;
      }

      // S: shortlist selected candidate
      if (key === 's') {
        e.preventDefault();
        if (selectedIndex >= 0 && selectedIndex < items.length) {
          onShortlist?.(items[selectedIndex]);
        }
        return;
      }

      // R: reject selected candidate
      if (key === 'r') {
        e.preventDefault();
        if (selectedIndex >= 0 && selectedIndex < items.length) {
          onReject?.(items[selectedIndex]);
        }
        return;
      }

      // Enter: open selected candidate
      if (key === 'Enter') {
        e.preventDefault();
        if (selectedIndex >= 0 && selectedIndex < items.length) {
          onOpen?.(items[selectedIndex]);
        }
        return;
      }
    },
    [enabled, items, selectedIndex, onSelect, onShortlist, onReject, onOpen, onSearch]
  );

  useEffect(() => {
    if (!enabled) return;
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [enabled, handleKeyDown]);

  return { selectedIndex };
}
