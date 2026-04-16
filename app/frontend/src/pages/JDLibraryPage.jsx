import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { LayoutTemplate, Plus, Trash2, Edit2, X, Save, Sparkles, TrendingUp, Filter } from 'lucide-react'
import { getTemplates, createTemplate, updateTemplate, deleteTemplate } from '../lib/api'

function TemplateModal({ template, onSave, onClose }) {
  const [name, setName] = useState(template?.name || '')
  const [jd, setJd] = useState(template?.jd_text || '')
  const [tags, setTags] = useState(template?.tags || '')
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    if (!name.trim() || !jd.trim()) return
    setSaving(true)
    try {
      await onSave({ name, jd_text: jd, tags })
      onClose()
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white/95 backdrop-blur-xl rounded-3xl ring-1 ring-brand-100 shadow-brand-xl w-full max-w-2xl max-h-[90vh] flex flex-col card-animate">
        <div className="flex items-center justify-between p-5 border-b border-brand-50">
          <h3 className="font-extrabold text-brand-900 tracking-tight">
            {template ? 'Edit Job Description' : 'New Job Description'}
          </h3>
          <button onClick={onClose} className="p-1.5 hover:bg-brand-50 rounded-xl transition-colors">
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1.5">JD Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder='e.g. "Senior Backend Engineer"'
              className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
            />
          </div>
          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1.5">
              Role Category / Tags
            </label>
            <input
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="technical, sales, hr, marketing, etc."
              className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
            />
          </div>
          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1.5">Job Description</label>
            <textarea
              value={jd}
              onChange={(e) => setJd(e.target.value)}
              placeholder="Paste the job description..."
              rows={10}
              className="w-full px-4 py-3 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 resize-none text-sm bg-white"
            />
            <p className="text-xs text-slate-500 mt-1">
              {jd.length} characters • {jd.split(/\s+/).filter(Boolean).length} words
            </p>
          </div>
        </div>
        <div className="flex justify-end gap-2 p-5 border-t border-brand-50">
          <button
            onClick={onClose}
            className="px-4 py-2 ring-1 ring-brand-200 text-sm font-semibold text-brand-700 rounded-xl hover:bg-brand-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !name.trim() || !jd.trim()}
            className="flex items-center gap-2 px-4 py-2 btn-brand text-white text-sm font-bold rounded-xl disabled:opacity-60 shadow-brand-sm"
          >
            <Save className="w-4 h-4" /> {saving ? 'Saving...' : 'Save JD'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function JDLibraryPage() {
  const navigate = useNavigate()
  const [templates, setTemplates] = useState([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [filterCategory, setFilterCategory] = useState('all')
  const [sortBy, setSortBy] = useState('recent')

  const load = () => getTemplates().then(setTemplates).finally(() => setLoading(false))
  useEffect(() => { load() }, [])

  const handleSave = async (data) => {
    if (editing) await updateTemplate(editing.id, data)
    else await createTemplate(data)
    setEditing(null)
    load()
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this job description?')) return
    await deleteTemplate(id)
    load()
  }

  const handleUse = (template) => {
    // Parse weights if available
    let weights = null
    if (template.scoring_weights) {
      try {
        weights = typeof template.scoring_weights === 'string' 
          ? JSON.parse(template.scoring_weights) 
          : template.scoring_weights
      } catch (e) {
        console.error('Failed to parse weights:', e)
      }
    }

    // Navigate to analyze page with JD and weights
    navigate('/analyze', { 
      state: { 
        jd_text: template.jd_text,
        weights: weights,
        role_category: template.tags
      } 
    })
  }

  // Get unique categories
  const categories = ['all', ...new Set(
    templates
      .map(t => t.tags?.toLowerCase().trim())
      .filter(Boolean)
  )]

  // Filter and sort templates
  let filteredTemplates = templates
  if (filterCategory !== 'all') {
    filteredTemplates = templates.filter(t => 
      t.tags?.toLowerCase().includes(filterCategory.toLowerCase())
    )
  }

  if (sortBy === 'recent') {
    filteredTemplates = [...filteredTemplates].sort((a, b) => 
      new Date(b.created_at) - new Date(a.created_at)
    )
  } else if (sortBy === 'name') {
    filteredTemplates = [...filteredTemplates].sort((a, b) => 
      a.name.localeCompare(b.name)
    )
  }

  // Parse weights for display
  const getWeights = (template) => {
    if (!template.scoring_weights) return null
    try {
      return typeof template.scoring_weights === 'string' 
        ? JSON.parse(template.scoring_weights) 
        : template.scoring_weights
    } catch (e) {
      return null
    }
  }

  return (
    <div>
      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between card-animate">
          <div>
            <h2 className="text-3xl font-extrabold text-brand-900 tracking-tight">JD Library</h2>
            <p className="text-slate-500 text-sm mt-1 font-medium">
              Saved job descriptions with AI-optimized scoring weights
            </p>
          </div>
          <button
            onClick={() => { setEditing(null); setModalOpen(true) }}
            className="flex items-center gap-2 px-4 py-2.5 btn-brand text-white text-sm font-bold rounded-xl shadow-brand-sm"
          >
            <Plus className="w-4 h-4" /> New JD
          </button>
        </div>

        {/* Filters */}
        {templates.length > 0 && (
          <div className="flex flex-wrap items-center gap-4 bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-brand-sm p-4 card-animate">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-slate-500" />
              <span className="text-sm font-semibold text-slate-700">Filter:</span>
              <div className="flex gap-1">
                {categories.map(cat => (
                  <button
                    key={cat}
                    onClick={() => setFilterCategory(cat)}
                    className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-all capitalize ${
                      filterCategory === cat
                        ? 'bg-brand-600 text-white shadow-brand-sm'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-2 ml-auto">
              <span className="text-sm font-semibold text-slate-700">Sort:</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="px-3 py-1.5 text-xs rounded-lg font-medium bg-slate-100 text-slate-600 border-0 focus:ring-2 focus:ring-brand-500"
              >
                <option value="recent">Recent</option>
                <option value="name">Name</option>
              </select>
            </div>
          </div>
        )}

        {/* Templates Grid */}
        {loading ? (
          <div className="flex justify-center py-16">
            <div className="w-8 h-8 border-4 border-brand-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : filteredTemplates.length === 0 ? (
          <div className="text-center py-16 bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand card-animate">
            <div className="w-16 h-16 rounded-2xl bg-brand-50 ring-1 ring-brand-200 flex items-center justify-center mx-auto mb-4">
              <LayoutTemplate className="w-8 h-8 text-brand-300" />
            </div>
            <p className="text-slate-500 font-medium mb-2">
              {filterCategory !== 'all' ? 'No JDs in this category' : 'No saved job descriptions yet'}
            </p>
            <p className="text-xs text-slate-400 mb-5">
              {filterCategory !== 'all' 
                ? 'Try a different filter or create a new JD' 
                : 'JDs are automatically saved when you run analyses, or create one manually'}
            </p>
            <button
              onClick={() => setModalOpen(true)}
              className="px-5 py-2.5 btn-brand text-white text-sm font-bold rounded-xl shadow-brand-sm"
            >
              Create JD
            </button>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredTemplates.map(t => {
              const weights = getWeights(t)
              return (
                <div 
                  key={t.id} 
                  className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-5 hover:shadow-brand-lg transition-shadow card-animate flex flex-col"
                >
                  {/* Header */}
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-extrabold text-brand-900 tracking-tight truncate">{t.name}</h3>
                      {t.tags && (
                        <div className="flex flex-wrap gap-1 mt-1.5">
                          {t.tags.split(',').map(tag => tag.trim()).filter(Boolean).slice(0, 2).map((tag, i) => (
                            <span 
                              key={i} 
                              className="px-2 py-0.5 bg-brand-50 text-brand-700 text-xs rounded-lg font-semibold ring-1 ring-brand-100 capitalize"
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="flex gap-1 shrink-0">
                      <button
                        onClick={() => { setEditing(t); setModalOpen(true) }}
                        className="p-1.5 hover:bg-brand-50 rounded-xl text-slate-400 hover:text-brand-700 transition-colors"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(t.id)}
                        className="p-1.5 hover:bg-red-50 rounded-xl text-slate-400 hover:text-red-600 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {/* JD Preview */}
                  <p className="text-sm text-slate-500 line-clamp-3 mb-3 leading-relaxed flex-1">
                    {t.jd_text}
                  </p>

                  {/* Weights Display */}
                  {weights && (
                    <div className="mb-3 p-3 bg-brand-50 rounded-2xl ring-1 ring-brand-100">
                      <div className="flex items-center gap-2 mb-2">
                        <TrendingUp className="w-3.5 h-3.5 text-brand-600" />
                        <span className="text-xs font-bold text-brand-800 uppercase tracking-wide">
                          Scoring Weights
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-x-3 gap-y-1">
                        {Object.entries(weights).slice(0, 4).map(([key, value]) => (
                          <div key={key} className="flex justify-between text-xs">
                            <span className="text-slate-600 capitalize truncate">
                              {key.replace(/_/g, ' ')}:
                            </span>
                            <span className="font-bold text-brand-700">
                              {Math.round(value * 100)}%
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Meta Info */}
                  <div className="flex items-center justify-between text-xs text-slate-400 mb-3">
                    <span>Created {new Date(t.created_at).toLocaleDateString()}</span>
                  </div>

                  {/* Use Button */}
                  <button
                    onClick={() => handleUse(t)}
                    className="w-full flex items-center justify-center gap-2 py-2.5 bg-brand-50 ring-1 ring-brand-200 text-brand-700 text-sm font-bold rounded-2xl hover:bg-brand-100 transition-colors"
                  >
                    <Sparkles className="w-4 h-4" /> Use This JD
                  </button>
                </div>
              )
            })}
          </div>
        )}
      </main>

      {modalOpen && (
        <TemplateModal
          template={editing}
          onSave={handleSave}
          onClose={() => { setModalOpen(false); setEditing(null) }}
        />
      )}
    </div>
  )
}
