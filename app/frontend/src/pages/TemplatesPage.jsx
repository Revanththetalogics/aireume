import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { LayoutTemplate, Plus, Trash2, Edit2, X, Save, Sparkles } from 'lucide-react'
import NavBar from '../components/NavBar'
import { getTemplates, createTemplate, updateTemplate, deleteTemplate } from '../lib/api'

function TemplateModal({ template, onSave, onClose }) {
  const [name, setName]   = useState(template?.name || '')
  const [jd, setJd]       = useState(template?.jd_text || '')
  const [tags, setTags]   = useState(template?.tags || '')
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
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-5 border-b border-slate-100">
          <h3 className="font-bold text-slate-900">{template ? 'Edit Template' : 'New Template'}</h3>
          <button onClick={onClose} className="p-1 hover:bg-slate-100 rounded"><X className="w-5 h-5 text-slate-500" /></button>
        </div>
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Template Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder='e.g. "Senior Python Developer"'
              className="w-full px-4 py-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Tags (comma-separated)</label>
            <input
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="engineering, python, senior"
              className="w-full px-4 py-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Job Description</label>
            <textarea
              value={jd}
              onChange={(e) => setJd(e.target.value)}
              placeholder="Paste the job description..."
              rows={10}
              className="w-full px-4 py-3 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 resize-none text-sm"
            />
          </div>
        </div>
        <div className="flex justify-end gap-2 p-5 border-t border-slate-100">
          <button onClick={onClose} className="px-4 py-2 border border-slate-300 text-sm text-slate-700 rounded-lg hover:bg-slate-50 transition-colors">Cancel</button>
          <button
            onClick={handleSave}
            disabled={saving || !name.trim() || !jd.trim()}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-60 transition-colors"
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
    if (editing) {
      await updateTemplate(editing.id, data)
    } else {
      await createTemplate(data)
    }
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
    <div className="min-h-screen bg-slate-50">
      <NavBar />
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-slate-900">Role Templates</h2>
            <p className="text-slate-500 text-sm mt-1">Save commonly used job descriptions for quick reuse.</p>
          </div>
          <button
            onClick={() => { setEditing(null); setModalOpen(true) }}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Plus className="w-4 h-4" /> New Template
          </button>
        </div>

        {loading ? (
          <div className="flex justify-center py-12">
            <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : templates.length === 0 ? (
          <div className="text-center py-16 bg-white rounded-xl border border-slate-200">
            <LayoutTemplate className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <p className="text-slate-500 mb-4">No templates yet. Create your first role template.</p>
            <button
              onClick={() => setModalOpen(true)}
              className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              Create Template
            </button>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 gap-4">
            {templates.map(t => (
              <div key={t.id} className="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div>
                    <h3 className="font-semibold text-slate-900">{t.name}</h3>
                    {t.tags && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {t.tags.split(',').map(tag => tag.trim()).filter(Boolean).map((tag, i) => (
                          <span key={i} className="px-2 py-0.5 bg-slate-100 text-slate-600 text-xs rounded-full">{tag}</span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="flex gap-1 shrink-0">
                    <button onClick={() => { setEditing(t); setModalOpen(true) }} className="p-1.5 hover:bg-slate-100 rounded text-slate-400 hover:text-slate-700 transition-colors">
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button onClick={() => handleDelete(t.id)} className="p-1.5 hover:bg-red-50 rounded text-slate-400 hover:text-red-600 transition-colors">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                <p className="text-sm text-slate-500 line-clamp-3 mb-4">{t.jd_text}</p>
                <button
                  onClick={() => handleUse(t)}
                  className="w-full flex items-center justify-center gap-2 py-2 bg-blue-50 text-blue-700 text-sm font-medium rounded-lg hover:bg-blue-100 transition-colors"
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
