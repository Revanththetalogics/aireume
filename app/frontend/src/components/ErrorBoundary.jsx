import React from 'react'
import * as Sentry from '@sentry/react'
import { AlertTriangle } from 'lucide-react'

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo)
    try {
      fetch('/api/client-error', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          message: String(error),
          stack: errorInfo?.componentStack?.slice(0, 2000),
        }),
      })
    } catch {
      /* reporting must never break the UI */
    }
    Sentry.captureException(error, { extra: { componentStack: errorInfo?.componentStack } })
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-surface dark:bg-dark-bg">
          <div className="max-w-md w-full bg-white dark:bg-dark-card rounded-2xl shadow-brand p-8 text-center ring-1 ring-brand-100 dark:ring-white/10">
            <AlertTriangle className="w-12 h-12 text-brand-600 mx-auto mb-4" aria-hidden="true" />
            <h2 className="text-xl font-semibold text-brand-900 dark:text-dark-text-primary mb-2">Something went wrong</h2>
            <p className="text-slate-600 dark:text-dark-text-secondary mb-6">
              An unexpected error occurred. Please try again or refresh the page.
            </p>
            <div className="space-x-3">
              <button
                type="button"
                onClick={this.handleRetry}
                className="px-4 py-2 bg-brand-600 text-white rounded-xl hover:bg-brand-700 transition-colors"
              >
                Try Again
              </button>
              <button
                type="button"
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-slate-200 dark:bg-white/10 text-slate-700 dark:text-dark-text-primary rounded-xl hover:bg-slate-300 transition-colors"
              >
                Refresh Page
              </button>
            </div>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

export default ErrorBoundary
