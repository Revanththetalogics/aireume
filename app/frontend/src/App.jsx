import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { NotificationProvider } from './contexts/NotificationContext'
import { OnboardingProvider, useOnboarding } from './contexts/OnboardingContext'
import { SubscriptionProvider } from './hooks/useSubscription'
import ProtectedRoute from './components/ProtectedRoute'
import PlatformAdminRoute from './components/PlatformAdminRoute'
import AppShell from './components/AppShell'
import ErrorBoundary from './components/ErrorBoundary'
import OnboardingWizard from './components/OnboardingWizard'

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
const TeamSkillsPage = lazy(() => import('./pages/TeamSkillsPage'))
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

function OnboardingGate({ children }) {
  const { isOnboardingComplete } = useOnboarding()
  const { user } = useAuth()

  if (user && !isOnboardingComplete) {
    return <OnboardingWizard />
  }

  return children
}

function App() {
  return (
    <AuthProvider>
      <SubscriptionProvider>
        <NotificationProvider>
          <OnboardingProvider>
            <ErrorBoundary>
              <Suspense fallback={<PageLoader />}>
                <Routes>
              {/* Public routes */}
              <Route path="/login"      element={<LoginPage />} />
              <Route path="/register"   element={<RegisterPage />} />
              
              {/* Onboarding direct-access route */}
              <Route path="/onboarding" element={<ProtectedRoute><OnboardingWizard /></ProtectedRoute>} />
              
              {/* New routes */}
              <Route path="/"           element={<Shell><OnboardingGate><DashboardNew /></OnboardingGate></Shell>} />
              <Route path="/analyze"    element={<Shell><OnboardingGate><AnalyzePage /></OnboardingGate></Shell>} />
              <Route path="/jd-library" element={<Shell><OnboardingGate><JDLibraryPage /></OnboardingGate></Shell>} />
              <Route path="/jd-library/:id/handoff" element={<Shell><OnboardingGate><HandoffPackage /></OnboardingGate></Shell>} />
              <Route path="/jd-library/:id/candidates" element={<Shell><OnboardingGate><JDCandidatesPage /></OnboardingGate></Shell>} />
              
              {/* Existing routes */}
              <Route path="/report"     element={<Shell><OnboardingGate><ReportPage /></OnboardingGate></Shell>} />
              <Route path="/candidates" element={<Shell><OnboardingGate><CandidatesPage /></OnboardingGate></Shell>} />
              <Route path="/candidates/:id" element={<Shell><OnboardingGate><CandidateProfilePage /></OnboardingGate></Shell>} />
              <Route path="/pipeline"    element={<Shell><OnboardingGate><KanbanBoard /></OnboardingGate></Shell>} />
              <Route path="/compare"    element={<Shell><OnboardingGate><ComparePage /></OnboardingGate></Shell>} />
              <Route path="/team"       element={<Shell><OnboardingGate><TeamPage /></OnboardingGate></Shell>} />
              <Route path="/team-skills" element={<Shell><OnboardingGate><TeamSkillsPage /></OnboardingGate></Shell>} />
              <Route path="/transcript" element={<Shell><OnboardingGate><TranscriptPage /></OnboardingGate></Shell>} />
              <Route path="/video"      element={<Shell><OnboardingGate><VideoPage /></OnboardingGate></Shell>} />
              <Route path="/analytics"  element={<Shell><OnboardingGate><AnalyticsPage /></OnboardingGate></Shell>} />
              <Route path="/settings"   element={<Shell><OnboardingGate><SettingsPage /></OnboardingGate></Shell>} />
              <Route path="/admin" element={<PlatformAdminRoute><Shell><OnboardingGate><AdminDashboardPage /></OnboardingGate></Shell></PlatformAdminRoute>} />
              <Route path="/admin/email-settings" element={<PlatformAdminRoute><Shell><OnboardingGate><EmailSettings /></OnboardingGate></Shell></PlatformAdminRoute>} />
              <Route path="/admin/security-events" element={<PlatformAdminRoute><Shell><OnboardingGate><SecurityEventsPage /></OnboardingGate></Shell></PlatformAdminRoute>} />
              <Route path="/admin/impersonation" element={<PlatformAdminRoute><Shell><OnboardingGate><ImpersonationPage /></OnboardingGate></Shell></PlatformAdminRoute>} />
              <Route path="/admin/erasure" element={<PlatformAdminRoute><Shell><OnboardingGate><ErasurePage /></OnboardingGate></Shell></PlatformAdminRoute>} />
              <Route path="/admin/plan-features" element={<PlatformAdminRoute><Shell><OnboardingGate><PlanFeaturesPage /></OnboardingGate></Shell></PlatformAdminRoute>} />

              {/* Backward compatibility redirects */}
              <Route path="/batch"      element={<Navigate to="/analyze" replace />} />
              <Route path="/templates"  element={<Navigate to="/jd-library" replace />} />
              
              {/* Legacy route for old dashboard (kept for compatibility) */}
              <Route path="/dashboard-old" element={<Shell><OnboardingGate><Dashboard /></OnboardingGate></Shell>} />
              
              {/* Catch all */}
              <Route path="*" element={
                <div className="flex flex-col items-center justify-center min-h-[60vh] text-slate-500">
                  <h1 className="text-6xl font-bold text-slate-300 mb-4">404</h1>
                  <p className="text-lg font-medium mb-2">Page not found</p>
                  <p className="text-sm mb-4">The page you're looking for doesn't exist.</p>
                  <a href="/" className="px-4 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600">Go Home</a>
                </div>
              } />
              </Routes>
              </Suspense>
            </ErrorBoundary>
          </OnboardingProvider>
        </NotificationProvider>
      </SubscriptionProvider>
    </AuthProvider>
  )
}

export default App
