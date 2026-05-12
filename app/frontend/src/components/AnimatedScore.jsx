import { useEffect } from 'react';
import { motion, useMotionValue, useTransform, animate } from 'framer-motion';
import { getScoreColor } from '../lib/constants';

/**
 * Animated score counter that counts up from 0 to target score.
 *
 * Props:
 * - score: number (0-100) — target score
 * - duration: number (default 0.8) — animation duration in seconds
 * - size: 'sm' | 'md' | 'lg' (default 'md') — text size
 * - showColor: boolean (default true) — whether to color-code based on score
 * - className: string — additional classes
 * - animate: boolean (default true) — whether to animate (false = static display)
 */
export default function AnimatedScore({
  score,
  duration = 0.8,
  size = 'md',
  showColor = true,
  className = '',
  animate: shouldAnimate = true,
}) {
  const count = useMotionValue(0);
  const rounded = useTransform(count, (latest) => Math.round(latest));

  const sizeClasses = {
    sm: 'text-lg font-bold',
    md: 'text-2xl font-bold',
    lg: 'text-4xl font-extrabold',
  };

  const colorConfig = getScoreColor(score);
  const colorClass = showColor && colorConfig ? colorConfig.text : 'text-slate-900';

  useEffect(() => {
    if (!shouldAnimate) {
      count.set(score);
      return;
    }

    const controls = animate(count, score, {
      duration,
      ease: 'easeOut',
    });

    return controls.stop;
  }, [score, duration, shouldAnimate, count]);

  return (
    <motion.span
      className={`${sizeClasses[size] || sizeClasses.md} ${colorClass} ${className}`}
    >
      {rounded}
    </motion.span>
  );
}
