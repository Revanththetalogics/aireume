import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { LayoutTemplate, Plus, Trash2, Edit2, X, Save, Sparkles } from 'lucide-react'
import { getTemplates, createTemplate, updateTemplate, deleteTemplate } from '../lib/api'

function TemplateModal({ template, onSave, onClose }) {
  const [name, setName]     = useState(template?.name || '')
  const [jd, setJd]         = useState(template?.jd_text || '')
  const [tags, setTags]     = useState(template?.tags || '')
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
          <h3 className="font-extrabold text-brand-900 tracking-tight">{template ? 'Edit Template' : 'New Template'}</h3>
          <button onClick={onClose} className="p-1.5 hover:bg-brand-50 rounded-xl transition-colors">
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1.5">Template Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder='e.g. "Senior Python Developer"'
              className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
            />
          </div>
          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1.5">Tags (comma-separated)</label>
            <input
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="engineering, python, senior"
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
            <Save className="w-4 h-4" /> {saving ? 'Saving...' : 'Save Template'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function TemplatesPage() {
  const navigate = useNavigate()
  const [templates, setTemplates] = useState([])
  const [loading, setLoading]     = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing]     = useState(null)

  const load = () => getTemplates().then(setTemplates).finally(() => setLoading(false))
  useEffect(() => { load() }, [])

  const handleSave = async (data) => {
    if (editing) await updateTemplate(editing.id, data)
    else await createTemplate(data)
    setEditing(null)
    load()
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this template?')) return
    await deleteTemplate(id)
    load()
  }

  const handleUse = (template) => {
    navigate('/', { state: { jdText: template.jd_text } })
  }

  return (
    <div>
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div className="flex items-center justify-between card-animate">
          <div>
            <h2 className="text-3xl font-extrabold text-brand-900 tracking-tight">Role Templates</h2>
            <p className="text-slate-500 text-sm mt-1 font-medium">Save commonly used job descriptions for quick reuse.</p>
          </div>
          <button
            onClick={() => { setEditing(null); setModalOpen(true) }}
            className="flex items-center gap-2 px-4 py-2.5 btn-brand text-white text-sm font-bold rounded-xl shadow-brand-sm"
          >
            <Plus className="w-4 h-4" /> New Template
          </button>
        </div>

        {loading ? (
          <div className="flex justify-center py-16">
            <div className="w-8 h-8 border-4 border-brand-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : templates.length === 0 ? (
          <div className="text-center py-16 bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand card-animate">
            <div className="w-16 h-16 rounded-2xl bg-brand-50 ring-1 ring-brand-200 flex items-center justify-center mx-auto mb-4">
              <LayoutTemplate className="w-8 h-8 text-brand-300" />
            </div>
            <p className="text-slate-500 font-medium mb-5">No templates yet. Create your first role template.</p>
            <button
              onClick={() => setModalOpen(true)}
              className="px-5 py-2.5 btn-brand text-white text-sm font-bold rounded-xl shadow-brand-sm"
            >
              Create Template
            </button>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 gap-4">
            {templates.map(t => (
              <div key={t.id} className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-5 hover:shadow-brand-lg transition-shadow card-animate">
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div>
                    <h3 className="font-extrabold text-brand-900 tracking-tight">{t.name}</h3>
                    {t.tags && (
                      <div className="flex flex-wrap gap-1 mt-1.5">
                        {t.tags.split(',').map(tag => tag.trim()).filter(Boolean).map((tag, i) => (
                          <span key={i} className="px-2 py-0.5 bg-brand-50 text-brand-700 text-xs rounded-lg font-semibold ring-1 ring-brand-100">{tag}</span>
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
                <p className="text-sm text-slate-500 line-clamp-3 mb-4 leading-relaxed">{t.jd_text}</p>
                <button
                  onClick={() => handleUse(t)}
                  className="w-full flex items-center justify-center gap-2 py-2.5 bg-brand-50 ring-1 ring-brand-200 text-brand-700 text-sm font-bold rounded-2xl hover:bg-brand-100 transition-colors"
                >
                  <Sparkles className="w-4 h-4" /> Use Template
                </button>
              </div>
            ))}
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
