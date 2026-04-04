import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import AppShell from './components/AppShell'

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
    <div className="h-screen bg-surface flex items-center justify-center">
      <div className="w-8 h-8 border-4 border-brand-600 border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

function Shell({ children }) {
  return (
    <ProtectedRoute>
      <AppShell>{children}</AppShell>
    </ProtectedRoute>
  )
}

function App() {
  return (
    <AuthProvider>
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route path="/login"      element={<LoginPage />} />
          <Route path="/register"   element={<RegisterPage />} />
          <Route path="/"           element={<Shell><Dashboard /></Shell>} />
          <Route path="/report"     element={<Shell><ReportPage /></Shell>} />
          <Route path="/batch"      element={<Shell><BatchPage /></Shell>} />
          <Route path="/candidates" element={<Shell><CandidatesPage /></Shell>} />
          <Route path="/compare"    element={<Shell><ComparePage /></Shell>} />
          <Route path="/templates"  element={<Shell><TemplatesPage /></Shell>} />
          <Route path="/team"       element={<Shell><TeamPage /></Shell>} />
          <Route path="/transcript" element={<Shell><TranscriptPage /></Shell>} />
          <Route path="/video"      element={<Shell><VideoPage /></Shell>} />
          <Route path="*"           element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </AuthProvider>
  )
}

export default App
