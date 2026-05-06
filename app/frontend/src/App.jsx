import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { SubscriptionProvider } from './hooks/useSubscription'
import ProtectedRoute from './components/ProtectedRoute'
import PlatformAdminRoute from './components/PlatformAdminRoute'
import AppShell from './components/AppShell'
import ErrorBoundary from './components/ErrorBoundary'

// New pages
const DashboardNew = lazy(() => import('./pages/DashboardNew'))
const AnalyzePage  = lazy(() => import('./pages/AnalyzePage'))
const JDLibraryPage = lazy(() => import('./pages/JDLibraryPage'))
const HandoffPackage = lazy(() => import('./components/HandoffPackage'))
const JDCandidatesPage = lazy(() => import('./pages/JDCandidatesPage'))

// Existing pages
const Dashboard    = lazy(() => import('./pages/Dashboard'))
const ReportPage   = lazy(() => import('./pages/ReportPage'))
const LoginPage    = lazy(() => import('./pages/LoginPage'))
const RegisterPage = lazy(() => import('./pages/RegisterPage'))
const CandidatesPage = lazy(() => import('./pages/CandidatesPage'))
const CandidateProfilePage = lazy(() => import('./pages/CandidateProfilePage'))
const KanbanBoard    = lazy(() => import('./pages/KanbanBoard'))
const ComparePage  = lazy(() => import('./pages/ComparePage'))
const TemplatesPage = lazy(() => import('./pages/TemplatesPage'))
const BatchPage    = lazy(() => import('./pages/BatchPage'))
const TeamPage       = lazy(() => import('./pages/TeamPage'))
const TranscriptPage = lazy(() => import('./pages/TranscriptPage'))
const VideoPage    = lazy(() => import('./pages/VideoPage'))
const SettingsPage = lazy(() => import('./pages/SettingsPage'))
const AdminDashboardPage = lazy(() => import('./pages/AdminDashboardPage'))
const AnalyticsPage  = lazy(() => import('./pages/AnalyticsPage'))
const EmailSettings = lazy(() => import('./pages/admin/EmailSettings'))
const SecurityEventsPage = lazy(() => import('./pages/admin/SecurityEventsPage'))
const ImpersonationPage = lazy(() => import('./pages/admin/ImpersonationPage'))
const ErasurePage = lazy(() => import('./pages/admin/ErasurePage'))
const PlanFeaturesPage = lazy(() => import('./pages/admin/PlanFeaturesPage'))

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
      <SubscriptionProvider>
        <AppShell>{children}</AppShell>
      </SubscriptionProvider>
    </ProtectedRoute>
  )
}

function App() {
  return (
    <AuthProvider>
      <ErrorBoundary>
        <Suspense fallback={<PageLoader />}>
          <Routes>
          {/* Public routes */}
          <Route path="/login"      element={<LoginPage />} />
          <Route path="/register"   element={<RegisterPage />} />
          
          {/* New routes */}
          <Route path="/"           element={<Shell><DashboardNew /></Shell>} />
          <Route path="/analyze"    element={<Shell><AnalyzePage /></Shell>} />
          <Route path="/jd-library" element={<Shell><JDLibraryPage /></Shell>} />
          <Route path="/jd-library/:id/handoff" element={<Shell><HandoffPackage /></Shell>} />
          <Route path="/jd-library/:id/candidates" element={<Shell><JDCandidatesPage /></Shell>} />
          
          {/* Existing routes */}
          <Route path="/report"     element={<Shell><ReportPage /></Shell>} />
          <Route path="/candidates" element={<Shell><CandidatesPage /></Shell>} />
          <Route path="/candidates/:id" element={<Shell><CandidateProfilePage /></Shell>} />
          <Route path="/pipeline"    element={<Shell><KanbanBoard /></Shell>} />
          <Route path="/compare"    element={<Shell><ComparePage /></Shell>} />
          <Route path="/team"       element={<Shell><TeamPage /></Shell>} />
          <Route path="/transcript" element={<Shell><TranscriptPage /></Shell>} />
          <Route path="/video"      element={<Shell><VideoPage /></Shell>} />
          <Route path="/analytics"  element={<Shell><AnalyticsPage /></Shell>} />
          <Route path="/settings"   element={<Shell><SettingsPage /></Shell>} />
          <Route path="/admin" element={<PlatformAdminRoute><Shell><AdminDashboardPage /></Shell></PlatformAdminRoute>} />
          <Route path="/admin/email-settings" element={<PlatformAdminRoute><Shell><EmailSettings /></Shell></PlatformAdminRoute>} />
          <Route path="/admin/security-events" element={<PlatformAdminRoute><Shell><SecurityEventsPage /></Shell></PlatformAdminRoute>} />
          <Route path="/admin/impersonation" element={<PlatformAdminRoute><Shell><ImpersonationPage /></Shell></PlatformAdminRoute>} />
          <Route path="/admin/erasure" element={<PlatformAdminRoute><Shell><ErasurePage /></Shell></PlatformAdminRoute>} />
          <Route path="/admin/plan-features" element={<PlatformAdminRoute><Shell><PlanFeaturesPage /></Shell></PlatformAdminRoute>} />

          {/* Backward compatibility redirects */}
          <Route path="/batch"      element={<Navigate to="/analyze" replace />} />
          <Route path="/templates"  element={<Navigate to="/jd-library" replace />} />
          
          {/* Legacy route for old dashboard (kept for compatibility) */}
          <Route path="/dashboard-old" element={<Shell><Dashboard /></Shell>} />
          
          {/* Catch all */}
          <Route path="*"           element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </ErrorBoundary>
    </AuthProvider>
  )
}

export default App
