import { useState, useEffect, useRef } from 'react';

/**
 * Typewriter-style text reveal for streaming LLM narrative content.
 *
 * Props:
 * - text: string — full text to display (can grow as streaming adds content)
 * - isStreaming: boolean — whether text is still being received
 * - speed: number (default 20) — characters per frame (batch reveal, not per-character)
 * - immediate: boolean (default false) — skip animation, show full text instantly
 * - className: string — text styling classes
 */
export default function StreamingText({
  text,
  isStreaming = false,
  speed = 20,
  immediate = false,
  className = '',
}) {
  const [displayedLength, setDisplayedLength] = useState(0);
  const prevTextRef = useRef('');

  useEffect(() => {
    if (!isStreaming) {
      // Not streaming: progressive typewriter reveal from start
      if (text !== prevTextRef.current) {
        // New text arrived; start typewriter from 0
        setDisplayedLength(0);
        prevTextRef.current = text;
      }

      // Skip animation when immediate prop is set or speed is 0
      if (immediate || speed === 0) {
        setDisplayedLength(text.length);
        return;
      }

      if (displayedLength < text.length) {
        let rafId;
        const step = () => {
          setDisplayedLength((prev) => {
            const next = Math.min(prev + speed, text.length);
            if (next < text.length) {
              rafId = requestAnimationFrame(step);
            }
            return next;
          });
        };
        rafId = requestAnimationFrame(step);
        return () => cancelAnimationFrame(rafId);
      }
    } else {
      // Streaming mode: reveal text as it grows
      if (text.length > displayedLength) {
        setDisplayedLength(text.length);
      }
      prevTextRef.current = text;
    }

  }, [text, isStreaming, speed, immediate, displayedLength]);

  const displayedText = text.slice(0, displayedLength);

  return (
    <span className={`leading-relaxed ${className}`}>
      {/* Visual typewriter animation is hidden from assistive tech to avoid
          per-character announcement chaos. */}
      <span aria-hidden="true">
        {displayedText}
        {isStreaming && (
          <span className="inline-block w-[2px] h-[1em] bg-purple-600 ml-0.5 align-middle animate-pulse" />
        )}
      </span>
      {/* Screen readers get the full text once, announced politely only after
          streaming completes (not on every incremental token). */}
      <span className="sr-only" aria-live="polite">
        {isStreaming ? '' : text}
      </span>
    </span>
  );
}
