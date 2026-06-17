import { useState, useEffect } from 'react'
import {
  CreditCard,
  Loader2,
  Check,
  X,
  Eye,
  EyeOff,
  Copy,
  Send,
  Settings,
  AlertTriangle,
  Save,
  TestTube,
  Link,
  Globe,
} from 'lucide-react'
import {
  getBillingSettings,
  updateBillingSettings,
  testBillingConnection,
  generateCheckoutLink,
  getAdminTenants,
  getAdminPlans,
  extractApiError,
} from '../../lib/api'

function Toast({ message, type = 'success', onDone }) {
  useEffect(() => {
    const t = setTimeout(onDone, 3000)
    return () => clearTimeout(t)
  }, [onDone])

  const bg = type === 'success' ? 'bg-brand-900' : 'bg-red-600'
  return (
    <div className={`fixed bottom-6 right-6 z-50 ${bg} text-white px-5 py-3 rounded-2xl shadow-brand-lg text-sm font-semibold card-animate flex items-center gap-2`}>
      {type === 'success' ? <Check className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
      {message}
    </div>
  )
}

function CopyButton({ text, label = 'Copy' }) {
  const [copied, setCopied] = useState(false)
  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // ignore
    }
  }
  return (
    <button
      onClick={handleCopy}
      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg ring-1 ring-brand-200 text-brand-700 hover:bg-brand-50 transition-colors"
      title={label}
    >
      {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
      {copied ? 'Copied' : label}
    </button>
  )
}

function MaskedInput({ label, value, onChange, placeholder = '', required = false }) {
  const [show, setShow] = useState(false)
  return (
    <div>
      <label className="block text-sm font-bold text-slate-700 mb-1.5">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <div className="relative">
        <input
          type={show ? 'text' : 'password'}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full px-4 py-2.5 pr-10 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white outline-none transition-all"
        />
        <button
          type="button"
          onClick={() => setShow((v) => !v)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
        >
          {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>
    </div>
  )
}

const PROVIDERS = [
  {
    key: 'stripe',
    label: 'Stripe',
    description: 'Credit cards, subscriptions, and invoicing',
    icon: <CreditCard className="w-6 h-6" />,
  },
  {
    key: 'razorpay',
    label: 'Razorpay',
    description: 'India-focused payments and UPI support',
    icon: <Globe className="w-6 h-6" />,
  },
  {
    key: 'manual',
    label: 'Manual',
    description: 'Offline invoicing and bank transfers',
    icon: <Settings className="w-6 h-6" />,
  },
]

export default function BillingSettingsPage() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testingStripe, setTestingStripe] = useState(false)
  const [testingRazorpay, setTestingRazorpay] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [toast, setToast] = useState(null)

  const [activeProvider, setActiveProvider] = useState('manual')
  const [stripeConfig, setStripeConfig] = useState({ secret_key: '', publishable_key: '', webhook_secret: '' })
  const [razorpayConfig, setRazorpayConfig] = useState({ key_id: '', key_secret: '', webhook_secret: '' })

  const [testResultStripe, setTestResultStripe] = useState(null)
  const [testResultRazorpay, setTestResultRazorpay] = useState(null)

  const [tenants, setTenants] = useState([])
  const [plans, setPlans] = useState([])
  const [selectedTenant, setSelectedTenant] = useState('')
  const [selectedPlan, setSelectedPlan] = useState('')
  const [checkoutResult, setCheckoutResult] = useState(null)

  const baseUrl = typeof window !== 'undefined' ? window.location.origin : ''
  const webhookUrl = `${baseUrl}/api/webhooks/billing`

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    Promise.all([getBillingSettings(), getAdminTenants(), getAdminPlans()])
      .then(([settings, tenantsData, plansData]) => {
        if (cancelled) return
        setActiveProvider(settings.active_provider || 'manual')
        setStripeConfig({
          secret_key: settings.stripe?.secret_key || '',
          publishable_key: settings.stripe?.publishable_key || '',
          webhook_secret: settings.stripe?.webhook_secret || '',
        })
        setRazorpayConfig({
          key_id: settings.razorpay?.key_id || '',
          key_secret: settings.razorpay?.key_secret || '',
          webhook_secret: settings.razorpay?.webhook_secret || '',
        })
        setTenants(tenantsData.tenants || tenantsData.items || [])
        setPlans(plansData.plans || [])
      })
      .catch((err) => {
        if (cancelled) return
        setToast({ message: `Failed to load billing settings: ${extractApiError(err)}`, type: 'error' })
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  async function handleSave() {
    setSaving(true)
    setTestResultStripe(null)
    setTestResultRazorpay(null)
    try {
      const payload = {
        active_provider: activeProvider,
        stripe: { ...stripeConfig },
        razorpay: { ...razorpayConfig },
      }
      await updateBillingSettings(payload)
      setToast({ message: 'Billing settings saved successfully', type: 'success' })
    } catch (err) {
      setToast({ message: `Failed to save: ${extractApiError(err)}`, type: 'error' })
    } finally {
      setSaving(false)
    }
  }

  async function handleTest(provider) {
    if (provider === 'stripe') {
      setTestingStripe(true)
      setTestResultStripe(null)
    } else {
      setTestingRazorpay(true)
      setTestResultRazorpay(null)
    }
    try {
      const res = await testBillingConnection(provider)
      if (provider === 'stripe') {
        setTestResultStripe(res)
      } else {
        setTestResultRazorpay(res)
      }
    } catch (err) {
      const msg = extractApiError(err)
      if (provider === 'stripe') {
        setTestResultStripe({ success: false, message: msg })
      } else {
        setTestResultRazorpay({ success: false, message: msg })
      }
    } finally {
      if (provider === 'stripe') setTestingStripe(false)
      else setTestingRazorpay(false)
    }
  }

  async function handleGenerateLink() {
    if (!selectedTenant || !selectedPlan) {
      setToast({ message: 'Please select a tenant and a plan', type: 'error' })
      return
    }
    setGenerating(true)
    setCheckoutResult(null)
    try {
      const res = await generateCheckoutLink(Number(selectedTenant), Number(selectedPlan))
      setCheckoutResult(res)
    } catch (err) {
      setToast({ message: `Failed to generate link: ${extractApiError(err)}`, type: 'error' })
    } finally {
      setGenerating(false)
    }
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
      </div>
    )
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8 card-animate">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-2xl bg-brand-50 ring-1 ring-brand-100 flex items-center justify-center">
            <CreditCard className="w-5 h-5 text-brand-600" />
          </div>
          <div>
            <h1 className="text-3xl font-extrabold text-brand-900 tracking-tight">Billing Settings</h1>
            <p className="text-slate-500 text-sm font-medium">Configure payment gateways and generate checkout links</p>
          </div>
        </div>
      </div>

      <div className="space-y-6">
        {/* Gateway Selector */}
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 card-animate">
          <h3 className="font-extrabold text-brand-900 tracking-tight mb-5">Payment Gateway</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {PROVIDERS.map((p) => {
              const isSelected = activeProvider === p.key
              return (
                <button
                  key={p.key}
                  onClick={() => {
                    setActiveProvider(p.key)
                    setTestResultStripe(null)
                    setTestResultRazorpay(null)
                  }}
                  className={`relative flex flex-col items-center gap-3 p-5 rounded-2xl border-2 text-center transition-all duration-150
                    ${isSelected
                      ? 'border-teal-500 bg-teal-50 shadow-sm'
                      : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
                    }`}
                >
                  <span className={`${isSelected ? 'text-teal-600' : 'text-slate-500'}`}>
                    {p.icon}
                  </span>
                  <div>
                    <p className={`text-sm font-bold ${isSelected ? 'text-teal-900' : 'text-slate-800'}`}>{p.label}</p>
                    <p className={`text-xs mt-0.5 ${isSelected ? 'text-teal-700' : 'text-slate-500'}`}>{p.description}</p>
                  </div>
                  {isSelected && (
                    <span className="absolute top-3 right-3 text-[10px] font-bold uppercase tracking-wider bg-teal-500 text-white px-2 py-0.5 rounded-full">
                      Active
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        </div>

        {/* Stripe Configuration */}
        {activeProvider === 'stripe' && (
          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 card-animate">
            <h3 className="font-extrabold text-brand-900 tracking-tight mb-5">Stripe Configuration</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div className="md:col-span-2">
                <MaskedInput
                  label="Secret Key"
                  value={stripeConfig.secret_key}
                  onChange={(v) => setStripeConfig((prev) => ({ ...prev, secret_key: v }))}
                  placeholder="sk_test_... or sk_live_..."
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-bold text-slate-700 mb-1.5">Publishable Key</label>
                <input
                  type="text"
                  value={stripeConfig.publishable_key}
                  onChange={(e) => setStripeConfig((prev) => ({ ...prev, publishable_key: e.target.value }))}
                  placeholder="pk_test_... or pk_live_..."
                  className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white outline-none transition-all"
                />
              </div>
              <div>
                <MaskedInput
                  label="Webhook Secret"
                  value={stripeConfig.webhook_secret}
                  onChange={(v) => setStripeConfig((prev) => ({ ...prev, webhook_secret: v }))}
                  placeholder="whsec_..."
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-bold text-slate-700 mb-1.5">Webhook Endpoint URL</label>
                <div className="flex items-center gap-3">
                  <input
                    type="text"
                    readOnly
                    value={webhookUrl}
                    className="flex-1 px-4 py-2.5 rounded-xl ring-1 ring-brand-200 text-sm bg-slate-50 text-slate-600 outline-none"
                  />
                  <CopyButton text={webhookUrl} label="Copy URL" />
                </div>
                <p className="text-xs text-slate-400 mt-1">Add this endpoint in your Stripe dashboard to receive billing events.</p>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 mt-8 pt-6 border-t border-brand-50">
              <button
                onClick={() => handleTest('stripe')}
                disabled={testingStripe || !stripeConfig.secret_key}
                className="flex items-center gap-2 px-5 py-2.5 ring-1 ring-brand-200 text-sm font-semibold text-brand-700 rounded-xl hover:bg-brand-50 transition-colors disabled:opacity-60"
              >
                {testingStripe ? <Loader2 className="w-4 h-4 animate-spin" /> : <TestTube className="w-4 h-4" />}
                {testingStripe ? 'Testing...' : 'Test Connection'}
              </button>
            </div>

            {testResultStripe && (
              <div className={`mt-4 p-3 rounded-xl ring-1 flex items-start gap-2.5 ${
                testResultStripe.success
                  ? 'bg-green-50 ring-green-200 text-green-700'
                  : 'bg-red-50 ring-red-200 text-red-700'
              }`}>
                {testResultStripe.success ? <Check className="w-4 h-4 mt-0.5 shrink-0" /> : <X className="w-4 h-4 mt-0.5 shrink-0" />}
                <p className="text-sm font-medium">{testResultStripe.message}</p>
              </div>
            )}
          </div>
        )}

        {/* Razorpay Configuration */}
        {activeProvider === 'razorpay' && (
          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 card-animate">
            <h3 className="font-extrabold text-brand-900 tracking-tight mb-5">Razorpay Configuration</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className="block text-sm font-bold text-slate-700 mb-1.5">Key ID</label>
                <input
                  type="text"
                  value={razorpayConfig.key_id}
                  onChange={(e) => setRazorpayConfig((prev) => ({ ...prev, key_id: e.target.value }))}
                  placeholder="rzp_test_... or rzp_live_..."
                  className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white outline-none transition-all"
                />
              </div>
              <div>
                <MaskedInput
                  label="Key Secret"
                  value={razorpayConfig.key_secret}
                  onChange={(v) => setRazorpayConfig((prev) => ({ ...prev, key_secret: v }))}
                  placeholder="Enter key secret"
                />
              </div>
              <div className="md:col-span-2">
                <MaskedInput
                  label="Webhook Secret"
                  value={razorpayConfig.webhook_secret}
                  onChange={(v) => setRazorpayConfig((prev) => ({ ...prev, webhook_secret: v }))}
                  placeholder="Enter webhook secret"
                />
              </div>
            </div>

            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 mt-8 pt-6 border-t border-brand-50">
              <button
                onClick={() => handleTest('razorpay')}
                disabled={testingRazorpay || !razorpayConfig.key_id || !razorpayConfig.key_secret}
                className="flex items-center gap-2 px-5 py-2.5 ring-1 ring-brand-200 text-sm font-semibold text-brand-700 rounded-xl hover:bg-brand-50 transition-colors disabled:opacity-60"
              >
                {testingRazorpay ? <Loader2 className="w-4 h-4 animate-spin" /> : <TestTube className="w-4 h-4" />}
                {testingRazorpay ? 'Testing...' : 'Test Connection'}
              </button>
            </div>

            {testResultRazorpay && (
              <div className={`mt-4 p-3 rounded-xl ring-1 flex items-start gap-2.5 ${
                testResultRazorpay.success
                  ? 'bg-green-50 ring-green-200 text-green-700'
                  : 'bg-red-50 ring-red-200 text-red-700'
              }`}>
                {testResultRazorpay.success ? <Check className="w-4 h-4 mt-0.5 shrink-0" /> : <X className="w-4 h-4 mt-0.5 shrink-0" />}
                <p className="text-sm font-medium">{testResultRazorpay.message}</p>
              </div>
            )}
          </div>
        )}

        {/* Save Button */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-5 py-2.5 btn-brand text-white text-sm font-bold rounded-xl shadow-brand-sm disabled:opacity-60 transition-all"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>

        {/* Checkout Link Generator */}
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 card-animate">
          <div className="flex items-center gap-3 mb-5">
            <Link className="w-5 h-5 text-brand-600" />
            <h3 className="font-extrabold text-brand-900 tracking-tight">Checkout Link Generator</h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
            <div>
              <label className="block text-sm font-bold text-slate-700 mb-1.5">Tenant</label>
              <select
                value={selectedTenant}
                onChange={(e) => setSelectedTenant(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white outline-none transition-all"
              >
                <option value="">Select tenant...</option>
                {tenants.map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-bold text-slate-700 mb-1.5">Plan</label>
              <select
                value={selectedPlan}
                onChange={(e) => setSelectedPlan(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white outline-none transition-all"
              >
                <option value="">Select plan...</option>
                {plans.map((p) => (
                  <option key={p.id} value={p.id}>{p.display_name || p.name}</option>
                ))}
              </select>
            </div>
            <button
              onClick={handleGenerateLink}
              disabled={generating || !selectedTenant || !selectedPlan || activeProvider === 'manual'}
              className="flex items-center justify-center gap-2 px-5 py-2.5 btn-brand text-white text-sm font-bold rounded-xl shadow-brand-sm disabled:opacity-60 transition-all"
            >
              {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Link className="w-4 h-4" />}
              {generating ? 'Generating...' : 'Generate Link'}
            </button>
          </div>

          {activeProvider === 'manual' && (
            <div className="mt-4 p-3 bg-amber-50/50 rounded-xl ring-1 ring-amber-100 flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
              <p className="text-sm text-amber-700">Checkout links are not available when using Manual billing. Switch to Stripe or Razorpay to generate checkout links.</p>
            </div>
          )}

          {checkoutResult && (
            <div className="mt-5 p-4 rounded-xl ring-1 ring-brand-200 bg-brand-50/30">
              <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                <input
                  type="text"
                  readOnly
                  value={checkoutResult.checkout_url}
                  className="flex-1 px-4 py-2.5 rounded-xl ring-1 ring-brand-200 text-sm bg-white text-slate-700 outline-none"
                />
                <div className="flex items-center gap-2">
                  <CopyButton text={checkoutResult.checkout_url} label="Copy Link" />
                  <button
                    onClick={() => {
                      const tenant = tenants.find((t) => String(t.id) === selectedTenant)
                      if (tenant?.contact_email) {
                        window.location.href = `mailto:${tenant.contact_email}?subject=Your ARIA Subscription Checkout Link&body=Here is your checkout link: ${checkoutResult.checkout_url}`
                      } else {
                        setToast({ message: 'Tenant has no contact email on file', type: 'error' })
                      }
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg ring-1 ring-brand-200 text-brand-700 hover:bg-brand-50 transition-colors"
                  >
                    <Send className="w-3.5 h-3.5" />
                    Email
                  </button>
                </div>
              </div>
              <p className="text-xs text-slate-500 mt-2">
                Expires at: {checkoutResult.expires_at ? new Date(checkoutResult.expires_at).toLocaleString() : 'N/A'}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Toast */}
      {toast && <Toast message={toast.message} type={toast.type} onDone={() => setToast(null)} />}
    </div>
  )
}
