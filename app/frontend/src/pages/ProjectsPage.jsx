import { useState, useEffect, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { FolderKanban, Plus, Loader2, Users, ChevronRight } from 'lucide-react'
import { listProjects, createProject, getTemplates } from '../lib/api'
import { Button } from '../components/ui'

const STATUS_STYLES = {
  draft: 'bg-slate-100 text-slate-700 ring-slate-200',
  active: 'bg-green-50 text-green-700 ring-green-200',
  paused: 'bg-amber-50 text-amber-700 ring-amber-200',
  closed: 'bg-red-50 text-red-700 ring-red-200',
}

export default function ProjectsPage() {
  const navigate = useNavigate()
  const [projects, setProjects] = useState([])
  const [templates, setTemplates] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState({ name: '', description: '', role_template_id: '', status: 'active' })
  const [filter, setFilter] = useState('all')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [projData, tplData] = await Promise.all([
        listProjects(filter === 'all' ? null : filter),
        getTemplates(),
      ])
      setProjects(Array.isArray(projData) ? projData : [])
      setTemplates(Array.isArray(tplData) ? tplData : [])
    } catch {
      setProjects([])
    } finally {
      setLoading(false)
    }
  }, [filter])

  useEffect(() => {
    load()
  }, [load])

  const handleCreate = async (e) => {
    e.preventDefault()
    if (!form.name.trim() || !form.role_template_id) return
    setCreating(true)
    try {
      const project = await createProject({
        name: form.name.trim(),
        description: form.description.trim() || null,
        role_template_id: Number(form.role_template_id),
        status: form.status,
      })
      setShowCreate(false)
      setForm({ name: '', description: '', role_template_id: '', status: 'active' })
      navigate(`/projects/${project.id}`)
    } catch (err) {
      window.alert(err.response?.data?.detail || 'Failed to create project')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center justify-between gap-4 mb-8 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-brand-50 ring-1 ring-brand-100 flex items-center justify-center">
            <FolderKanban className="w-5 h-5 text-brand-600" />
          </div>
          <div>
            <h1 className="text-3xl font-extrabold text-brand-900 tracking-tight">Screening Projects</h1>
            <p className="text-slate-500 text-sm font-medium">Organize hiring pushes with project-scoped pipelines</p>
          </div>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="w-4 h-4" />
          New Project
        </Button>
      </div>

      <div className="flex gap-2 mb-6 flex-wrap">
        {['all', 'active', 'draft', 'paused', 'closed'].map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold capitalize transition-colors ${
              filter === s ? 'bg-brand-600 text-white' : 'text-slate-600 hover:bg-brand-50 ring-1 ring-brand-100'
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {showCreate && (
        <form onSubmit={handleCreate} className="mb-8 bg-white/90 rounded-2xl ring-1 ring-brand-100 p-6 space-y-4">
          <h2 className="font-bold text-brand-900">Create screening project</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <label className="block text-sm sm:col-span-2">
              <span className="font-semibold text-slate-700">Project name</span>
              <input
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                className="mt-1 w-full rounded-xl border border-brand-200 px-3 py-2 text-sm"
                required
              />
            </label>
            <label className="block text-sm sm:col-span-2">
              <span className="font-semibold text-slate-700">Description</span>
              <textarea
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                rows={2}
                className="mt-1 w-full rounded-xl border border-brand-200 px-3 py-2 text-sm resize-none"
              />
            </label>
            <label className="block text-sm">
              <span className="font-semibold text-slate-700">Role template (JD)</span>
              <select
                value={form.role_template_id}
                onChange={(e) => setForm((f) => ({ ...f, role_template_id: e.target.value }))}
                className="mt-1 w-full rounded-xl border border-brand-200 px-3 py-2 text-sm"
                required
              >
                <option value="">Select template…</option>
                {templates.map((t) => (
                  <option key={t.id} value={t.id}>{t.name || t.title || `Template ${t.id}`}</option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              <span className="font-semibold text-slate-700">Status</span>
              <select
                value={form.status}
                onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))}
                className="mt-1 w-full rounded-xl border border-brand-200 px-3 py-2 text-sm"
              >
                <option value="active">Active</option>
                <option value="draft">Draft</option>
              </select>
            </label>
          </div>
          <div className="flex gap-2 justify-end">
            <Button type="button" variant="secondary" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button type="submit" disabled={creating}>
              {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Create'}
            </Button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="w-8 h-8 text-brand-500 animate-spin" />
        </div>
      ) : projects.length === 0 ? (
        <div className="text-center py-16 rounded-2xl ring-1 ring-brand-100 bg-brand-50/20">
          <FolderKanban className="w-12 h-12 text-brand-300 mx-auto mb-3" />
          <p className="text-slate-500">No projects yet. Create one to start tracking a hiring push.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {projects.map((p) => (
            <Link
              key={p.id}
              to={`/projects/${p.id}`}
              className="group rounded-2xl ring-1 ring-brand-100 bg-white/90 p-5 hover:ring-brand-300 hover:shadow-brand transition-all"
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="font-bold text-brand-900 group-hover:text-brand-700">{p.name}</h3>
                  {p.description && (
                    <p className="text-sm text-slate-500 mt-1 line-clamp-2">{p.description}</p>
                  )}
                </div>
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ring-1 capitalize shrink-0 ${STATUS_STYLES[p.status] || STATUS_STYLES.draft}`}>
                  {p.status}
                </span>
              </div>
              <div className="flex items-center gap-4 mt-4 text-sm text-slate-500">
                <span className="inline-flex items-center gap-1">
                  <Users className="w-4 h-4" />
                  {p.candidate_count ?? 0} candidates
                </span>
                <ChevronRight className="w-4 h-4 ml-auto text-brand-400 group-hover:translate-x-0.5 transition-transform" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
