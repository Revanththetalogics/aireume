import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { 
  Sparkles, TrendingUp, Users, LayoutTemplate, ArrowRight, 
  Clock, CheckCircle, BarChart3, Zap, Shield, Brain, FileText
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useSubscription } from '../hooks/useSubscription'
import { getTemplates } from '../lib/api'

export default function DashboardNew() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { subscription, getUsageStats, loading } = useSubscription()
  const [savedJds, setSavedJds] = useState([])
  const [recentAnalyses, setRecentAnalyses] = useState([])

  const usage = getUsageStats()

  // Load saved JDs
  useEffect(() => {
    getTemplates()
      .then((res) => {
        const arr = Array.isArray(res) ? res : res?.templates || []
        setSavedJds(arr.slice(0, 3)) // Show top 3
      })
      .catch(() => setSavedJds([]))
  }, [])

  // TODO: Load recent analyses from API
  // For now, using placeholder data
  useEffect(() => {
    // This would be replaced with actual API call
    // const fetchRecentAnalyses = async () => {
    //   const data = await getRecentAnalyses(5)
    //   setRecentAnalyses(data)
    // }
    // fetchRecentAnalyses()
  }, [])

  const isUnlimited = usage?.analysesLimit < 0
  const percentUsed = usage?.percentUsed || 0

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Welcome Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-extrabold text-brand-900 tracking-tight">
          Welcome back{user?.email ? `, ${user.email.split('@')[0]}` : ''}
        </h1>
        <p className="text-slate-500 text-sm mt-1 font-medium">
          Your AI-powered resume screening dashboard
        </p>
      </div>

      {/* Quick Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {/* Usage Stats */}
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 card-animate">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-brand-50 flex items-center justify-center">
              <BarChart3 className="w-5 h-5 text-brand-600" />
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Usage This Month</p>
              <p className="text-2xl font-bold text-brand-900">
                {isUnlimited ? '∞' : usage?.analysesUsed || 0}
                {!isUnlimited && <span className="text-sm text-slate-500 font-normal"> / {usage?.analysesLimit || 0}</span>}
              </p>
            </div>
          </div>
          {!isUnlimited && (
            <div className="w-full bg-slate-100 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all ${
                  percentUsed > 90 ? 'bg-red-500' : percentUsed > 70 ? 'bg-amber-500' : 'bg-brand-500'
                }`}
                style={{ width: `${Math.min(percentUsed, 100)}%` }}
              />
            </div>
          )}
          {isUnlimited && (
            <div className="flex items-center gap-1 text-xs text-green-600 font-medium">
              <Sparkles className="w-3 h-3" />
              Unlimited analyses
            </div>
          )}
        </div>

        {/* Plan Info */}
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 card-animate">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-purple-50 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Current Plan</p>
              <p className="text-2xl font-bold text-purple-900 capitalize">
                {subscription?.current_plan?.plan?.name || 'Free'}
              </p>
            </div>
          </div>
          <Link
            to="/settings"
            className="text-xs text-purple-600 hover:text-purple-700 font-medium flex items-center gap-1"
          >
            Manage subscription
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>

        {/* Saved JDs */}
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 card-animate">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-green-50 flex items-center justify-center">
              <LayoutTemplate className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide">JD Library</p>
              <p className="text-2xl font-bold text-green-900">
                {savedJds.length}
              </p>
            </div>
          </div>
          <Link
            to="/jd-library"
            className="text-xs text-green-600 hover:text-green-700 font-medium flex items-center gap-1"
          >
            View all templates
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
      </div>

      {/* Hero CTA */}
      <div className="bg-gradient-to-br from-brand-600 to-brand-500 rounded-3xl shadow-brand-xl p-8 mb-8 card-animate">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-white/20 text-white text-xs font-semibold rounded-full mb-4">
              <Sparkles className="w-3.5 h-3.5" />
              AI-Powered Analysis
            </div>
            <h2 className="text-2xl font-extrabold text-white mb-2">
              Ready to analyze resumes?
            </h2>
            <p className="text-brand-100 text-sm mb-6 max-w-lg">
              Upload job description, get AI-suggested weights, and analyze single or multiple resumes with our 6-agent LangGraph pipeline.
            </p>
            <button
              onClick={() => navigate('/analyze')}
              className="inline-flex items-center gap-2 px-6 py-3 bg-white text-brand-700 rounded-2xl font-bold hover:shadow-lg transition-all shadow-md"
            >
              <Sparkles className="w-5 h-5" />
              New Analysis
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
          <div className="hidden lg:flex items-center gap-4">
            <div className="flex flex-col gap-3">
              {[
                { icon: Zap, label: '6-Agent Pipeline' },
                { icon: Brain, label: 'LLM-Driven' },
                { icon: Shield, label: 'Zero Data Leak' }
              ].map(({ icon: Icon, label }) => (
                <div key={label} className="flex items-center gap-2 text-white/90">
                  <div className="w-8 h-8 rounded-lg bg-white/20 flex items-center justify-center">
                    <Icon className="w-4 h-4" />
                  </div>
                  <span className="text-sm font-medium">{label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Analyses */}
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 card-animate">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-bold text-brand-900">Recent Analyses</h3>
            <Link
              to="/candidates"
              className="text-sm text-brand-600 hover:text-brand-700 font-medium flex items-center gap-1"
            >
              View all
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          {recentAnalyses.length > 0 ? (
            <div className="space-y-3">
              {recentAnalyses.map((analysis, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-3 p-4 bg-slate-50 rounded-2xl hover:bg-brand-50 transition-colors cursor-pointer ring-1 ring-slate-100 hover:ring-brand-200"
                  onClick={() => navigate(`/report?id=${analysis.id}`)}
                >
                  <div className="w-10 h-10 rounded-xl bg-brand-100 flex items-center justify-center shrink-0">
                    <FileText className="w-5 h-5 text-brand-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-brand-900 truncate">
                      {analysis.candidate_name || 'Candidate'}
                    </p>
                    <p className="text-xs text-slate-500">
                      {analysis.role || 'Position'} • {analysis.date}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`px-2.5 py-1 rounded-full text-xs font-bold ring-1 ${
                      analysis.fit_score >= 72 
                        ? 'bg-green-50 text-green-700 ring-green-200'
                        : analysis.fit_score >= 45
                        ? 'bg-amber-50 text-amber-700 ring-amber-200'
                        : 'bg-red-50 text-red-700 ring-red-200'
                    }`}>
                      {analysis.fit_score}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <div className="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mx-auto mb-4">
                <Clock className="w-8 h-8 text-slate-400" />
              </div>
              <p className="text-sm font-medium text-slate-600 mb-2">No analyses yet</p>
              <p className="text-xs text-slate-500 mb-4">Start your first analysis to see results here</p>
              <button
                onClick={() => navigate('/analyze')}
                className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-xl text-sm font-medium hover:bg-brand-700 transition-colors"
              >
                <Sparkles className="w-4 h-4" />
                Start Now
              </button>
            </div>
          )}
        </div>

        {/* Saved JD Library Quick Access */}
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 card-animate">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-bold text-brand-900">Quick Access JDs</h3>
            <Link
              to="/jd-library"
              className="text-sm text-brand-600 hover:text-brand-700 font-medium flex items-center gap-1"
            >
              View all
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          {savedJds.length > 0 ? (
            <div className="space-y-3">
              {savedJds.map((jd) => (
                <div
                  key={jd.id}
                  className="flex items-center gap-3 p-4 bg-slate-50 rounded-2xl hover:bg-brand-50 transition-colors cursor-pointer ring-1 ring-slate-100 hover:ring-brand-200"
                  onClick={() => navigate('/analyze', { 
                    state: { 
                      jd_text: jd.jd_text,
                      weights: jd.scoring_weights ? JSON.parse(jd.scoring_weights) : null,
                      role_category: jd.tags
                    } 
                  })}
                >
                  <div className="w-10 h-10 rounded-xl bg-green-100 flex items-center justify-center shrink-0">
                    <LayoutTemplate className="w-5 h-5 text-green-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-brand-900 truncate">{jd.name}</p>
                    <p className="text-xs text-slate-500">
                      {new Date(jd.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <ArrowRight className="w-4 h-4 text-slate-400" />
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <div className="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mx-auto mb-4">
                <LayoutTemplate className="w-8 h-8 text-slate-400" />
              </div>
              <p className="text-sm font-medium text-slate-600 mb-2">No saved JDs yet</p>
              <p className="text-xs text-slate-500 mb-4">JDs are automatically saved when you run analyses</p>
              <button
                onClick={() => navigate('/analyze')}
                className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-xl text-sm font-medium hover:bg-brand-700 transition-colors"
              >
                <Sparkles className="w-4 h-4" />
                Create First Analysis
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Feature Highlights */}
      <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          {
            icon: Sparkles,
            title: 'AI Weight Suggestions',
            desc: 'Get intelligent scoring weights based on job requirements',
            color: 'brand'
          },
          {
            icon: Users,
            title: 'Batch Processing',
            desc: 'Analyze multiple resumes at once with comparative ranking',
            color: 'purple'
          },
          {
            icon: TrendingUp,
            title: 'Version History',
            desc: 'Compare different analyses and track improvements',
            color: 'green'
          }
        ].map(({ icon: Icon, title, desc, color }) => (
          <div key={title} className="bg-white/70 backdrop-blur-sm rounded-2xl ring-1 ring-brand-100 p-4 card-animate">
            <div className={`w-10 h-10 rounded-xl bg-${color}-50 flex items-center justify-center mb-3`}>
              <Icon className={`w-5 h-5 text-${color}-600`} />
            </div>
            <h4 className="text-sm font-semibold text-brand-900 mb-1">{title}</h4>
            <p className="text-xs text-slate-500">{desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
