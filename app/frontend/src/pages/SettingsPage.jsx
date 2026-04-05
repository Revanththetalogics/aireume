import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Settings,
  User,
  Building2,
  CreditCard,
  Bell,
  Shield,
  Key,
  ChevronRight,
  Check,
  Loader2,
  AlertTriangle,
  Sparkles,
  Users,
  Zap,
  BarChart3,
  Calendar,
  RefreshCw
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useSubscription } from '../hooks/useSubscription'
import { adminResetUsage, adminChangePlan } from '../lib/api'

function Section({ title, icon: Icon, children, description }) {
  return (
    <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 card-animate">
      <div className="flex items-start gap-4 mb-5">
        <div className="w-10 h-10 rounded-2xl bg-brand-50 ring-1 ring-brand-100 flex items-center justify-center shrink-0">
          <Icon className="w-5 h-5 text-brand-600" />
        </div>
        <div>
          <h3 className="font-extrabold text-brand-900 text-lg tracking-tight">{title}</h3>
          {description && <p className="text-sm text-slate-500 mt-0.5">{description}</p>}
        </div>
      </div>
      {children}
    </div>
  )
}

function ProgressBar({ value, max, color = 'brand' }) {
  const percentage = Math.min(100, Math.round((value / max) * 100))
  const colorClasses = {
    brand: 'bg-brand-500',
    green: 'bg-green-500',
    amber: 'bg-amber-500',
    red: 'bg-red-500'
  }
  return (
    <div className="w-full bg-slate-100 rounded-full h-2">
      <div
        className={`h-2 rounded-full transition-all duration-500 ${colorClasses[color] || colorClasses.brand}`}
        style={{ width: `${percentage}%` }}
      />
    </div>
  )
}

function UsageCard({ label, used, limit, unit = '' }) {
  const isUnlimited = limit === -1
  const percentage = isUnlimited ? 0 : Math.round((used / limit) * 100)
  const color = percentage > 90 ? 'red' : percentage > 70 ? 'amber' : 'brand'

  return (
    <div className="p-4 bg-brand-50/50 rounded-2xl ring-1 ring-brand-100">
      <div className="flex justify-between items-center mb-2">
        <span className="text-sm font-medium text-slate-700">{label}</span>
        <span className={`text-xs font-bold ${percentage > 90 ? 'text-red-600' : 'text-brand-700'}`}>
          {isUnlimited ? `${used.toLocaleString()} / ∞` : `${used.toLocaleString()} / ${limit.toLocaleString()} ${unit}`}
        </span>
      </div>
      {!isUnlimited && <ProgressBar value={used} max={limit} color={color} />}
      {isUnlimited && (
        <div className="flex items-center gap-1 text-xs text-green-600 font-medium">
          <Sparkles className="w-3.5 h-3.5" />
          Unlimited
        </div>
      )}
    </div>
  )
}

export default function SettingsPage() {
  const navigate = useNavigate()
  const { user, tenant, logout } = useAuth()
  const {
    subscription,
    availablePlans,
    loading,
    error,
    fetchSubscription,
    getUsageStats,
    getCurrentPlan,
    isFeatureAvailable,
    getRemainingAnalyses,
  } = useSubscription()
  const [activeTab, setActiveTab] = useState('subscription')
  const [saving, setSaving] = useState(false)
  const [adminLoading, setAdminLoading] = useState(false)

  // Profile form state
  const [profile, setProfile] = useState({
    name: user?.email?.split('@')[0] || '',
    email: user?.email || '',
    notifications: {
      emailOnComplete: true,
      emailOnBatchComplete: true,
      marketing: false
    }
  })

  const handleSaveProfile = async () => {
    setSaving(true)
    await new Promise(r => setTimeout(r, 500))
    setSaving(false)
  }

  const handleResetUsage = async () => {
    if (!confirm('Reset usage counters? This is for testing only.')) return
    setAdminLoading(true)
    try {
      await adminResetUsage()
      await fetchSubscription(true)
      alert('Usage counters reset successfully')
    } catch (err) {
      alert('Failed to reset: ' + err.message)
    } finally {
      setAdminLoading(false)
    }
  }

  const handleChangePlan = async (planId) => {
    if (!confirm(`Switch to ${planId} plan?`)) return
    setAdminLoading(true)
    try {
      await adminChangePlan(planId)
      await fetchSubscription(true)
      alert(`Switched to ${planId} plan`)
    } catch (err) {
      alert('Failed to change plan: ' + err.message)
    } finally {
      setAdminLoading(false)
    }
  }

  const tabs = [
    { id: 'subscription', label: 'Subscription', icon: CreditCard },
    { id: 'team', label: 'Team & Access', icon: Users },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'security', label: 'Security', icon: Shield },
  ]

  const usageStats = getUsageStats()
  const currentPlan = getCurrentPlan()
  const remainingAnalyses = getRemainingAnalyses()

  // Get plan features list
  const planFeatures = currentPlan?.plan?.features || []

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8 card-animate">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-2xl bg-brand-50 ring-1 ring-brand-100 flex items-center justify-center">
            <Settings className="w-5 h-5 text-brand-600" />
          </div>
          <div>
            <h1 className="text-3xl font-extrabold text-brand-900 tracking-tight">Settings</h1>
            <p className="text-slate-500 text-sm font-medium">
              Manage your account, subscription, and preferences
            </p>
          </div>
        </div>
      </div>

      <div className="flex flex-col lg:flex-row gap-8">
        {/* Sidebar */}
        <div className="lg:w-64 shrink-0">
          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-2 sticky top-24">
            {tabs.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-2xl text-sm font-medium transition-all ${
                  activeTab === id
                    ? 'bg-brand-50 text-brand-700 ring-1 ring-brand-200'
                    : 'text-slate-600 hover:bg-brand-50/50 hover:text-brand-700'
                }`}
              >
                <Icon className={`w-4 h-4 ${activeTab === id ? 'text-brand-600' : 'text-slate-400'}`} />
                {label}
                {activeTab === id && <ChevronRight className="w-4 h-4 ml-auto" />}
              </button>
            ))}
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 space-y-6">
          {/* Subscription Tab */}
          {activeTab === 'subscription' && (
            <>
              {loading ? (
                <div className="flex justify-center py-16">
                  <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
                </div>
              ) : error ? (
                <div className="p-6 bg-red-50 rounded-2xl ring-1 ring-red-200 text-center">
                  <AlertTriangle className="w-8 h-8 text-red-500 mx-auto mb-2" />
                  <p className="text-red-700">{error}</p>
                  <button
                    onClick={() => fetchSubscription(true)}
                    className="mt-4 px-4 py-2 bg-white text-red-600 text-sm font-semibold rounded-xl hover:bg-red-50 transition-colors"
                  >
                    Retry
                  </button>
                </div>
              ) : (
                <>
                  {/* Current Plan */}
                  <Section
                    title="Current Plan"
                    icon={Zap}
                    description={currentPlan?.plan?.description || `You're on the ${currentPlan?.plan?.display_name || 'Free'} plan.`}
                  >
                    <div className="flex items-center justify-between p-4 bg-gradient-to-br from-brand-50 to-brand-100/50 rounded-2xl ring-1 ring-brand-200 mb-6">
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="font-extrabold text-brand-900 text-xl">{currentPlan?.plan?.display_name}</h4>
                          <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-bold rounded-full ring-1 ring-green-200">
                            {currentPlan?.status === 'active' ? 'Active' : currentPlan?.status}
                          </span>
                        </div>
                        <p className="text-sm text-slate-600 mt-1">
                          {currentPlan?.price > 0
                            ? `$${(currentPlan.price / 100).toFixed(0)}/${currentPlan?.billing_cycle === 'monthly' ? 'mo' : 'yr'}`
                            : 'Free plan'
                          }
                        </p>
                      </div>
                      <div className="text-right">
                        {usageStats?.daysUntilReset !== undefined && (
                          <p className="text-xs text-slate-500">
                            Resets in <span className="font-medium text-slate-700">{usageStats.daysUntilReset} days</span>
                          </p>
                        )}
                        {currentPlan?.current_period_end && (
                          <p className="text-xs text-slate-500 mt-1">
                            Period ends: <span className="font-medium text-slate-700">{new Date(currentPlan.current_period_end).toLocaleDateString()}</span>
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Usage Stats */}
                    <h5 className="font-bold text-slate-800 text-sm mb-3 flex items-center gap-2">
                      <BarChart3 className="w-4 h-4 text-brand-600" />
                      Usage This Month
                    </h5>
                    <div className="grid sm:grid-cols-2 gap-3">
                      <UsageCard
                        label="Resume Analyses"
                        used={usageStats?.analysesUsed || 0}
                        limit={usageStats?.analysesLimit || 20}
                      />
                      <UsageCard
                        label="Storage Used"
                        used={usageStats?.storageUsedMB || 0}
                        limit={(usageStats?.storageLimitGB || 1) * 1024}
                        unit="MB"
                      />
                      <UsageCard
                        label="Team Members"
                        used={usageStats?.teamMembers || 1}
                        limit={usageStats?.teamMembersLimit || 1}
                      />
                      <UsageCard
                        label="Remaining Analyses"
                        used={remainingAnalyses === Infinity ? 0 : (usageStats?.analysesLimit || 20) - (usageStats?.analysesUsed || 0)}
                        limit={remainingAnalyses === Infinity ? -1 : usageStats?.analysesLimit || 20}
                      />
                    </div>

                    {/* Features */}
                    <h5 className="font-bold text-slate-800 text-sm mt-6 mb-3 flex items-center gap-2">
                      <Check className="w-4 h-4 text-brand-600" />
                      Plan Features
                    </h5>
                    <div className="grid sm:grid-cols-2 gap-2">
                      {planFeatures.map((feature, i) => (
                        <div key={i} className="flex items-center gap-2 text-sm text-slate-700">
                          <div className="w-5 h-5 rounded-full bg-brand-50 flex items-center justify-center shrink-0">
                            <Check className="w-3 h-3 text-brand-600" />
                          </div>
                          {feature}
                        </div>
                      ))}
                    </div>

                    {/* Admin Controls */}
                    {user?.role === 'admin' && (
                      <>
                        <h5 className="font-bold text-slate-800 text-sm mt-6 mb-3 flex items-center gap-2">
                          <Sparkles className="w-4 h-4 text-brand-600" />
                          Admin Testing Controls
                        </h5>
                        <div className="flex gap-2 flex-wrap">
                          <button
                            onClick={handleResetUsage}
                            disabled={adminLoading}
                            className="flex items-center gap-2 px-3 py-2 bg-amber-50 text-amber-700 text-xs font-semibold rounded-xl hover:bg-amber-100 transition-colors disabled:opacity-50"
                          >
                            <RefreshCw className={`w-3 h-3 ${adminLoading ? 'animate-spin' : ''}`} />
                            Reset Usage
                          </button>
                        </div>
                      </>
                    )}
                  </Section>

                  {/* Available Plans */}
                  <Section
                    title="Available Plans"
                    icon={CreditCard}
                    description="Upgrade or change your plan at any time"
                  >
                    <div className="grid sm:grid-cols-3 gap-4">
                      {availablePlans.map((plan, index) => {
                        const isCurrent = currentPlan?.plan?.id === plan.id
                        const isPopular = plan.name === 'pro'
                        return (
                          <div
                            key={plan.id}
                            className={`relative p-5 rounded-2xl ring-1 transition-all ${
                              isCurrent
                                ? 'bg-brand-50 ring-brand-300'
                                : isPopular
                                  ? 'bg-white ring-brand-200 shadow-brand'
                                  : 'bg-white ring-brand-100'
                            } ${isCurrent ? '' : 'hover:shadow-brand-lg'}`}
                          >
                            {isPopular && !isCurrent && (
                              <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-brand-600 text-white text-xs font-bold rounded-full shadow-brand-sm">
                                Most Popular
                              </div>
                            )}
                            {isCurrent && (
                              <div className="absolute top-3 right-3 w-6 h-6 rounded-full bg-brand-600 text-white flex items-center justify-center">
                                <Check className="w-4 h-4" />
                              </div>
                            )}
                            <h4 className="font-extrabold text-brand-900 text-lg">{plan.display_name}</h4>
                            <p className="text-2xl font-bold text-brand-900 mt-1">
                              ${(plan.price_monthly / 100).toFixed(0)}
                              <span className="text-sm font-medium text-slate-500">/mo</span>
                            </p>
                            <p className="text-xs text-slate-500 mt-1">{plan.description}</p>
                            <ul className="mt-4 space-y-2">
                              {plan.features.slice(0, 5).map((feature, i) => (
                                <li key={i} className="flex items-center gap-2 text-xs text-slate-700">
                                  <div className="w-4 h-4 rounded-full bg-brand-50 flex items-center justify-center shrink-0">
                                    <Check className="w-2.5 h-2.5 text-brand-600" />
                                  </div>
                                  {feature}
                                </li>
                              ))}
                            </ul>
                            {user?.role === 'admin' ? (
                              <button
                                onClick={() => handleChangePlan(plan.id)}
                                disabled={isCurrent || adminLoading}
                                className={`w-full mt-4 py-2.5 rounded-xl text-sm font-bold transition-all ${
                                  isCurrent
                                    ? 'bg-brand-200 text-brand-700 cursor-default'
                                    : 'btn-brand text-white shadow-brand-sm disabled:opacity-50'
                                }`}
                              >
                                {isCurrent ? 'Current Plan' : adminLoading ? 'Changing...' : 'Switch Plan'}
                              </button>
                            ) : (
                              <button
                                disabled={isCurrent}
                                className={`w-full mt-4 py-2.5 rounded-xl text-sm font-bold transition-all ${
                                  isCurrent
                                    ? 'bg-brand-200 text-brand-700 cursor-default'
                                    : 'bg-slate-100 text-slate-400 cursor-not-allowed'
                                }`}
                              >
                                {isCurrent ? 'Current Plan' : 'Contact Admin'}
                              </button>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </Section>
                </>
              )}
            </>
          )}

          {/* Team & Access Tab */}
          {activeTab === 'team' && (
            <>
              <Section
                title="Organization"
                icon={Building2}
                description="Manage your team and tenant settings"
              >
                <div className="space-y-4">
                  <div className="p-4 bg-brand-50/50 rounded-2xl ring-1 ring-brand-100">
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wide mb-1">Organization Name</label>
                    <p className="font-semibold text-brand-900">{tenant?.name || 'Your Organization'}</p>
                  </div>
                  <div className="p-4 bg-brand-50/50 rounded-2xl ring-1 ring-brand-100">
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wide mb-1">Tenant ID</label>
                    <p className="font-mono text-sm text-slate-600">{tenant?.slug || 'your-org'}</p>
                  </div>
                  <div className="flex gap-2 mt-4">
                    <button
                      onClick={() => navigate('/team')}
                      className="flex items-center gap-2 px-4 py-2.5 btn-brand text-white text-sm font-bold rounded-xl shadow-brand-sm"
                    >
                      <Users className="w-4 h-4" />
                      Manage Team Members
                    </button>
                  </div>
                </div>
              </Section>

              <Section
                title="API Access"
                icon={Key}
                description="API keys for integrations"
              >
                <div className="p-4 bg-slate-50 rounded-2xl ring-1 ring-slate-200">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm font-medium text-slate-700">API Key</span>
                    <span className={`px-2 py-0.5 text-xs font-bold rounded-full ring-1 ${
                      isFeatureAvailable('api_access')
                        ? 'bg-brand-100 text-brand-700 ring-brand-200'
                        : 'bg-amber-100 text-amber-700 ring-amber-200'
                    }`}>
                      {isFeatureAvailable('api_access') ? 'Available' : 'Pro Required'}
                    </span>
                  </div>
                  {isFeatureAvailable('api_access') ? (
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value="••••••••••••••••••••••••••"
                        readOnly
                        className="flex-1 px-4 py-2 bg-white rounded-xl text-sm font-mono text-slate-500 ring-1 ring-slate-200"
                      />
                      <button className="px-4 py-2 bg-brand-50 text-brand-700 text-sm font-semibold rounded-xl hover:bg-brand-100 transition-colors">
                        Reveal
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 text-sm text-slate-500">
                      <AlertTriangle className="w-4 h-4 text-amber-500" />
                      Upgrade to Pro to access API keys
                    </div>
                  )}
                </div>
              </Section>
            </>
          )}

          {/* Notifications Tab */}
          {activeTab === 'notifications' && (
            <Section
              title="Notification Preferences"
              icon={Bell}
              description="Control when and how you receive updates"
            >
              <div className="space-y-4">
                {[{
                  id: 'emailOnComplete',
                  label: 'Email when analysis completes',
                  description: 'Receive an email when a single resume analysis is finished'
                }, {
                  id: 'emailOnBatchComplete',
                  label: 'Email when batch completes',
                  description: 'Receive an email summary when a batch screening is finished'
                }, {
                  id: 'marketing',
                  label: 'Product updates & tips',
                  description: 'Occasional emails about new features and best practices'
                }].map(({ id, label, description }) => (
                  <label
                    key={id}
                    className="flex items-start gap-4 p-4 bg-brand-50/30 rounded-2xl ring-1 ring-brand-100 cursor-pointer hover:bg-brand-50/50 transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={profile.notifications[id]}
                      onChange={(e) => setProfile(prev => ({
                        ...prev,
                        notifications: { ...prev.notifications, [id]: e.target.checked }
                      }))}
                      className="mt-0.5 w-5 h-5 rounded-lg border-brand-300 text-brand-600 focus:ring-brand-500"
                    />
                    <div className="flex-1">
                      <p className="font-semibold text-slate-800 text-sm">{label}</p>
                      <p className="text-xs text-slate-500 mt-0.5">{description}</p>
                    </div>
                  </label>
                ))}
              </div>
              <div className="flex justify-end mt-6">
                <button
                  onClick={handleSaveProfile}
                  disabled={saving}
                  className="flex items-center gap-2 px-5 py-2.5 btn-brand text-white text-sm font-bold rounded-xl shadow-brand-sm disabled:opacity-60"
                >
                  {saving ? <><Loader2 className="w-4 h-4 animate-spin" /> Saving...</> : <><Check className="w-4 h-4" /> Save Preferences</>}
                </button>
              </div>
            </Section>
          )}

          {/* Security Tab */}
          {activeTab === 'security' && (
            <>
              <Section
                title="Account Security"
                icon={Shield}
                description="Manage your password and security settings"
              >
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1.5">Email Address</label>
                    <input
                      type="email"
                      value={profile.email}
                      disabled
                      className="w-full px-4 py-2.5 bg-slate-50 rounded-xl text-sm text-slate-500 ring-1 ring-slate-200 cursor-not-allowed"
                    />
                    <p className="text-xs text-slate-400 mt-1">Contact support to change your email</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1.5">Current Password</label>
                    <input
                      type="password"
                      placeholder="••••••••"
                      disabled
                      className="w-full px-4 py-2.5 bg-slate-50 rounded-xl text-sm text-slate-500 ring-1 ring-slate-200 cursor-not-allowed"
                    />
                  </div>

                  <div className="flex gap-2 pt-2">
                    <button
                      onClick={() => alert('Password change coming soon')}
                      className="px-4 py-2.5 bg-brand-50 text-brand-700 text-sm font-semibold rounded-xl hover:bg-brand-100 transition-colors"
                    >
                      Change Password
                    </button>
                  </div>
                </div>
              </Section>

              <Section
                title="Danger Zone"
                icon={AlertTriangle}
                description="Actions that can't be undone"
              >
                <div className="p-4 bg-red-50/50 rounded-2xl ring-1 ring-red-200">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-bold text-red-800 text-sm">Delete Account</h4>
                      <p className="text-xs text-red-600 mt-0.5">This will permanently delete your account and all data</p>
                    </div>
                    <button
                      onClick={() => {
                        if (confirm('Are you sure? This cannot be undone.')) logout()
                      }}
                      className="px-4 py-2 bg-red-100 text-red-700 text-sm font-semibold rounded-xl hover:bg-red-200 transition-colors"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </Section>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
