import { Toaster } from 'react-hot-toast'

export default function ToastProvider() {
  return (
    <Toaster
      position="bottom-right"
      toastOptions={{
        duration: 4000,
        style: {
          background: '#ffffff',
          color: '#1e293b',
          fontFamily: "'Inter', system-ui, sans-serif",
          fontSize: '0.875rem',
          fontWeight: 500,
          borderRadius: '1rem',
          padding: '14px 18px',
          boxShadow: '0 8px 32px rgba(124,58,237,0.14)',
          border: '1px solid #EDE9FE',
          animation: 'fadeInUp 0.35s cubic-bezier(0.34, 1.56, 0.64, 1)',
        },
        success: {
          duration: 4000,
          iconTheme: {
            primary: '#7C3AED',
            secondary: '#ffffff',
          },
        },
        error: {
          duration: 5000,
          iconTheme: {
            primary: '#EF4444',
            secondary: '#ffffff',
          },
        },
        loading: {
          duration: Infinity,
          iconTheme: {
            primary: '#7C3AED',
            secondary: '#ffffff',
          },
        },
      }}
      containerStyle={{
        bottom: 24,
        right: 24,
        zIndex: 9999,
      }}
    />
  )
}
