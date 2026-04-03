import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'

const Dashboard    = lazy(() => import('./pages/Dashboard'))
const ReportPage   = lazy(() => import('./pages/ReportPage'))
const LoginPage    = lazy(() => import('./pages/LoginPage'))
const RegisterPage = lazy(() => import('./pages/RegisterPage'))
const CandidatesPage = lazy(() => import('./pages/CandidatesPage'))
const ComparePage  = lazy(() => import('./pages/ComparePage'))
const TemplatesPage = lazy(() => import('./pages/TemplatesPage'))
const BatchPage    = lazy(() => import('./pages/BatchPage'))
const TeamPage       = lazy(() => import('./pages/TeamPage'))
const TranscriptPage = lazy(() => import('./pages/TranscriptPage'))
const VideoPage    = lazy(() => import('./pages/VideoPage'))

function PageLoader() {
  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center">
      <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

function App() {
  return (
    <AuthProvider>
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route path="/login"    element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/"         element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/report"   element={<ProtectedRoute><ReportPage /></ProtectedRoute>} />
          <Route path="/batch"    element={<ProtectedRoute><BatchPage /></ProtectedRoute>} />
          <Route path="/candidates" element={<ProtectedRoute><CandidatesPage /></ProtectedRoute>} />
          <Route path="/compare"  element={<ProtectedRoute><ComparePage /></ProtectedRoute>} />
          <Route path="/templates" element={<ProtectedRoute><TemplatesPage /></ProtectedRoute>} />
          <Route path="/team"       element={<ProtectedRoute><TeamPage /></ProtectedRoute>} />
          <Route path="/transcript" element={<ProtectedRoute><TranscriptPage /></ProtectedRoute>} />
          <Route path="/video"    element={<ProtectedRoute><VideoPage /></ProtectedRoute>} />
          <Route path="*"         element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </AuthProvider>
  )
}

export default App
