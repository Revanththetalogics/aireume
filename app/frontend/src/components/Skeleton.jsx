// Reusable skeleton loader with variants
// Uses the existing 'shimmer' animation from tailwind.config.js

const baseClasses = 'bg-slate-200 animate-pulse rounded'

/**
 * Single skeleton element.
 *
 * @param {'text'|'card'|'list'|'circle'|'bar'} variant
 * @param {string}  [width]   - CSS width override
 * @param {string}  [height]  - CSS height override
 * @param {number}  [count=1] - Repeat N times
 * @param {string}  [className] - Extra Tailwind classes
 */
function Skeleton({ variant = 'text', width, height, count = 1, className = '' }) {
  const elements = []

  for (let i = 0; i < count; i++) {
    switch (variant) {
      case 'text':
        elements.push(
          <div key={i} className={`space-y-2 ${className}`}>
            <div className={`${baseClasses} h-4 w-full`} style={width ? { width } : undefined} />
          </div>
        )
        break

      case 'card':
        elements.push(
          <div
            key={i}
            className={`bg-white rounded-xl shadow-sm border border-slate-100 p-6 animate-pulse ${className}`}
            style={height ? { height } : undefined}
          >
            <div className="h-4 bg-slate-200 rounded w-1/2 mb-3" />
            <div className="h-8 bg-slate-200 rounded w-1/3 mb-4" />
            <div className="space-y-2">
              <div className="h-3 bg-slate-200 rounded w-3/4" />
              <div className="h-3 bg-slate-200 rounded w-1/2" />
            </div>
          </div>
        )
        break

      case 'list':
        elements.push(
          <div
            key={i}
            className={`flex items-center gap-3 p-3 animate-pulse ${className}`}
          >
            {/* Avatar circle */}
            <div className="w-9 h-9 rounded-full bg-slate-200 shrink-0" />
            {/* Text lines */}
            <div className="flex-1 space-y-2">
              <div className="h-4 bg-slate-200 rounded w-2/3" />
              <div className="h-3 bg-slate-200 rounded w-1/2" />
            </div>
            {/* Score badge placeholder */}
            <div className="h-6 w-12 rounded-full bg-slate-200 shrink-0" />
          </div>
        )
        break

      case 'circle':
        elements.push(
          <div
            key={i}
            className={`${baseClasses} rounded-full shrink-0 ${className}`}
            style={{
              width: width || '40px',
              height: height || width || '40px',
            }}
          />
        )
        break

      case 'bar':
        elements.push(
          <div
            key={i}
            className={`${baseClasses} rounded-full ${className}`}
            style={{
              width: width || '60%',
              height: height || '8px',
            }}
          />
        )
        break

      default:
        elements.push(
          <div key={i} className={`${baseClasses} h-4 w-full ${className}`} />
        )
    }
  }

  return count === 1 && variant !== 'card' ? elements[0] : <>{elements}</>
}

// ─── Sub-components for composable usage ─────────────────────────────────────

Skeleton.Text = function SkeletonText(props) {
  return <Skeleton variant="text" {...props} />
}

Skeleton.Card = function SkeletonCard(props) {
  return <Skeleton variant="card" {...props} />
}

Skeleton.List = function SkeletonList(props) {
  return <Skeleton variant="list" {...props} />
}

Skeleton.Circle = function SkeletonCircle(props) {
  return <Skeleton variant="circle" {...props} />
}

Skeleton.Bar = function SkeletonBar(props) {
  return <Skeleton variant="bar" {...props} />
}

export default Skeleton
