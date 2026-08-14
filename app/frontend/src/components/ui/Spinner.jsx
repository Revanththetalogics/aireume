export default function Spinner({ className = 'w-8 h-8', label = 'Loading' }) {
  return (
    <div
      role="status"
      aria-label={label}
      className={`border-4 border-brand-600 border-t-transparent rounded-full animate-spin ${className}`}
    />
  )
}
