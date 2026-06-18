import { motion } from 'framer-motion'
import { Clock } from 'lucide-react'

export default function SessionTimeoutModal({ countdown, onStayLoggedIn, onLogoutNow }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
      />
      <motion.div
        initial={{ opacity: 0, scale: 0.9, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ type: 'spring', stiffness: 350, damping: 28 }}
        className="relative bg-white rounded-2xl shadow-2xl max-w-sm w-full overflow-hidden"
      >
        {/* Header */}
        <div className="p-6 border-b border-slate-200 bg-gradient-to-r from-amber-50 to-orange-50 text-center">
          <div className="mx-auto w-14 h-14 rounded-full bg-amber-100 flex items-center justify-center mb-3">
            <Clock className="w-7 h-7 text-amber-600" />
          </div>
          <h2 className="text-xl font-bold text-slate-800">
            Session Expiring
          </h2>
        </div>

        {/* Body */}
        <div className="px-6 py-5 text-center">
          <p className="text-sm text-slate-600 leading-relaxed">
            Your session will expire due to inactivity in{' '}
            <span className="font-bold text-amber-600 text-lg">{countdown}</span>{' '}
            second{countdown !== 1 ? 's' : ''}.
          </p>
          <p className="text-xs text-slate-400 mt-2">
            Click "Stay Logged In" to continue your session.
          </p>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 flex items-center justify-end gap-3">
          <button
            onClick={onLogoutNow}
            className="px-5 py-2.5 text-sm font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-all"
          >
            Log Out Now
          </button>
          <button
            onClick={onStayLoggedIn}
            className="px-5 py-2.5 text-sm font-semibold text-white bg-teal-600 rounded-lg hover:bg-teal-700 transition-all shadow-sm hover:shadow-md"
          >
            Stay Logged In
          </button>
        </div>
      </motion.div>
    </div>
  )
}
