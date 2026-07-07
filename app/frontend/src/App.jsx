import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate, useLocation, useParams } from 'react-router-dom'
import { AnimatePresence, motion, MotionConfig } from 'framer-motion'
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
const ForgotPasswordPage = lazy(() => import('./pages/ForgotPasswordPage'))
const ResetPasswordPage = lazy(() => import('./pages/ResetPasswordPage'))
const VerifyEmailPage = lazy(() => import('./pages/VerifyEmailPage'))
const CheckEmailPage = lazy(() => import('./pages/CheckEmailPage'))
const CandidatesPage = lazy(() => import('./pages/CandidatesPage'))
const CandidateProfilePage = lazy(() => import('./pages/CandidateProfilePage'))
const ProjectsPage = lazy(() => import('./pages/ProjectsPage'))
const ProjectDetailPage = lazy(() => import('./pages/ProjectDetailPage'))
const KanbanBoard    = lazy(() => import('./pages/KanbanBoard'))
const ComparePage  = lazy(() => import('./pages/ComparePage'))
const TeamPage       = lazy(() => import('./pages/TeamPage'))
const TeamSkillsPage = lazy(() => import('./pages/TeamSkillsPage'))
const TranscriptPage = lazy(() => import('./pages/TranscriptPage'))
const VideoPage    = lazy(() => import('./pages/VideoPage'))
const SettingsPage = lazy(() => import('./pages/SettingsPage'))
const AnalyticsPage  = lazy(() => import('./pages/AnalyticsPage'))
const VoiceScreeningPage = lazy(() => import('./pages/VoiceScreeningPage'))
const RecruiterInterviewPage = lazy(() => import('./pages/RecruiterInterviewPage'))
const RecruiterSessionDetailPage = lazy(() => import('./pages/RecruiterSessionDetailPage'))
const InterviewPage = lazy(() => import('./pages/InterviewPage'))
const InterviewDetailPage = lazy(() => import('./pages/InterviewDetailPage'))
const InterviewComparisonPage = lazy(() => import('./pages/InterviewComparisonPage'))

// Admin layout + pages
const AdminLayout        = lazy(() => import('./layouts/AdminLayout'))
const AdminOverviewPage  = lazy(() => import('./pages/admin/AdminOverviewPage'))
const TenantsPage        = lazy(() => import('./pages/admin/TenantsPage'))
const TenantDetailPage   = lazy(() => import('./pages/admin/TenantDetailPage'))
const PlansPage          = lazy(() => import('./pages/admin/PlanManagementPage'))
const UsersPage          = lazy(() => import('./pages/admin/UsersPage'))
const FeatureFlagsPage   = lazy(() => import('./pages/admin/FeatureFlagsPage'))
const WebhooksPage       = lazy(() => import('./pages/admin/WebhooksPage'))
const RateLimitsPage     = lazy(() => import('./pages/admin/RateLimitsPage'))
const SSOPage            = lazy(() => import('./pages/admin/SSOPage'))
const EmailSettingsPage  = lazy(() => import('./pages/admin/EmailSettings'))
const MetricsPage        = lazy(() => import('./pages/admin/MetricsPage'))
const AuditLogPage       = lazy(() => import('./pages/admin/AuditLogPage'))
const SecurityEventsPage = lazy(() => import('./pages/admin/SecurityEventsPage'))
const RevenuePage        = lazy(() => import('./pages/admin/RevenuePage'))
const InvoicesPage       = lazy(() => import('./pages/admin/InvoicesPage'))
const DunningPage        = lazy(() => import('./pages/admin/DunningPage'))
const BillingSettingsPage = lazy(() => import('./pages/admin/BillingSettingsPage'))
const ErasurePage        = lazy(() => import('./pages/admin/ErasurePage'))
const ImpersonationPage  = lazy(() => import('./pages/admin/ImpersonationPage'))

function PageLoader() {
  return (
    <div className="h-screen bg-surface flex items-center justify-center">
      <div className="w-8 h-8 border-4 border-brand-600 border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

function Shell({ children }) {
  const location = useLocation()
  return (
    <ProtectedRoute>
      <SubscriptionProvider>
        <AppShell>
          {/* Per-route boundary: a crash in one page keeps the NavBar and
              other app chrome mounted, and resets when the route changes. */}
          <ErrorBoundary key={location.pathname}>
            {children}
          </ErrorBoundary>
        </AppShell>
      </SubscriptionProvider>
    </ProtectedRoute>
  )
}

function OnboardingGate({ children }) {
  const { isOnboardingComplete, statusLoading } = useOnboarding()
  const { user, tenant, loading: authLoading } = useAuth()

  // Wait for auth, onboarding status, and tenant to all be loaded before deciding
  const isLoading = authLoading || statusLoading || !user || !tenant

  if (isLoading) {
    return <PageLoader />
  }

  // If user is authenticated and onboarding is not complete (from backend or tenant data),
  // show the onboarding wizard
  const tenantOnboardingComplete = tenant?.onboarding_completed === true
  if (user && !isOnboardingComplete && !tenantOnboardingComplete) {
    return <OnboardingWizard />
  }

  return children
}

function App() {
  const location = useLocation()

  return (
    <MotionConfig reducedMotion="user">
    <AuthProvider>
        <NotificationProvider>
          <OnboardingProvider>
            <ErrorBoundary>
              <Suspense fallback={<PageLoader />}>
                <AnimatePresence mode="wait">
                <motion.div key={location.pathname}>
                <Routes>
              {/* Public routes */}
              <Route path="/login"      element={<LoginPage />} />
              <Route path="/register"   element={<RegisterPage />} />
              <Route path="/forgot-password" element={<ForgotPasswordPage />} />
              <Route path="/reset-password/:token" element={<ResetPasswordPage />} />
              <Route path="/verify-email/:token" element={<VerifyEmailPage />} />
              <Route path="/check-email" element={<CheckEmailPage />} />
              
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
              <Route path="/projects"    element={<Shell><OnboardingGate><ProjectsPage /></OnboardingGate></Shell>} />
              <Route path="/projects/:id" element={<Shell><OnboardingGate><ProjectDetailPage /></OnboardingGate></Shell>} />
              <Route path="/compare"    element={<Shell><OnboardingGate><ComparePage /></OnboardingGate></Shell>} />
              <Route path="/team"       element={<Shell><OnboardingGate><TeamPage /></OnboardingGate></Shell>} />
              <Route path="/team-skills" element={<Shell><OnboardingGate><TeamSkillsPage /></OnboardingGate></Shell>} />
              <Route path="/transcript" element={<Shell><OnboardingGate><TranscriptPage /></OnboardingGate></Shell>} />
              <Route path="/video"      element={<Shell><OnboardingGate><VideoPage /></OnboardingGate></Shell>} />
              <Route path="/analytics"  element={<Shell><OnboardingGate><AnalyticsPage /></OnboardingGate></Shell>} />
              <Route path="/voice-screening" element={<Shell><OnboardingGate><VoiceScreeningPage /></OnboardingGate></Shell>} />
              <Route path="/recruiter-interviews" element={<Shell><OnboardingGate><RecruiterInterviewPage /></OnboardingGate></Shell>} />
              <Route path="/recruiter-interviews/:id" element={<Shell><OnboardingGate><RecruiterSessionDetailPage /></OnboardingGate></Shell>} />
              <Route path="/ai-interviews" element={<Shell><OnboardingGate><InterviewPage /></OnboardingGate></Shell>} />
              <Route path="/ai-interviews/:id" element={<Shell><OnboardingGate><InterviewDetailPage /></OnboardingGate></Shell>} />
              <Route path="/interviews/comparison" element={<Shell><OnboardingGate><InterviewComparisonPage /></OnboardingGate></Shell>} />
              <Route path="/settings"   element={<Shell><OnboardingGate><SettingsPage /></OnboardingGate></Shell>} />
              {/* Admin portal - standalone layout (no recruiter nav) */}
              <Route path="/admin" element={<PlatformAdminRoute><AdminLayout /></PlatformAdminRoute>}>
                <Route index element={<AdminOverviewPage />} />
                <Route path="tenants/:id" element={<TenantDetailPage />} />
                <Route path="tenants" element={<TenantsPage />} />
                <Route path="plans" element={<PlansPage />} />
                <Route path="users" element={<UsersPage />} />
                <Route path="features" element={<FeatureFlagsPage />} />
                <Route path="webhooks" element={<WebhooksPage />} />
                <Route path="rate-limits" element={<RateLimitsPage />} />
                <Route path="sso" element={<SSOPage />} />
                <Route path="email" element={<EmailSettingsPage />} />
                <Route path="metrics" element={<MetricsPage />} />
                <Route path="audit" element={<AuditLogPage />} />
                <Route path="security" element={<SecurityEventsPage />} />
                <Route path="billing" element={<RevenuePage />} />
                <Route path="billing-settings" element={<BillingSettingsPage />} />
                <Route path="invoices" element={<InvoicesPage />} />
                <Route path="dunning" element={<DunningPage />} />
                <Route path="erasure" element={<ErasurePage />} />
                <Route path="impersonation" element={<ImpersonationPage />} />
              </Route>

              {/* Legacy redirects for unified AI Interview */}
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
              </motion.div>
              </AnimatePresence>
              </Suspense>
            </ErrorBoundary>
          </OnboardingProvider>
        </NotificationProvider>
    </AuthProvider>
    </MotionConfig>
  )
}

export default App
