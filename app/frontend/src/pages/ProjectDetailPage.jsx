import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  ArrowLeft, FolderKanban, Loader2, Users, Settings2,
} from 'lucide-react'
import {
  getProject,
  getProjectPipeline,
  updateProject,
  updateProjectCandidateStatus,
} from '../lib/api'
import { PIPELINE_STAGES } from '../lib/constants'
import usePermissions from '../hooks/usePermissions'
import { ViewerReadOnlyBanner } from '../components/RequireWriteAccess'

const COLUMN_STYLES = {
  pending: { header: 'bg-amber-50 text-amber-800 border-amber-200', badge: 'bg-amber-100 text-amber-700' },
  'in-review': { header: 'bg-blue-50 text-blue-800 border-blue-200', badge: 'bg-blue-100 text-blue-700' },
  shortlisted: { header: 'bg-green-50 text-green-800 border-green-200', badge: 'bg-green-100 text-green-700' },
  rejected: { header: 'bg-red-50 text-red-800 border-red-200', badge: 'bg-red-100 text-red-700' },
  hired: { header: 'bg-indigo-50 text-indigo-800 border-indigo-200', badge: 'bg-indigo-100 text-indigo-700' },
}

function CandidateCard({ item, onStatusChange, readOnly }) {
  const navigate = useNavigate()
  return (
    <div className="bg-white rounded-xl ring-1 ring-brand-100 p-3 shadow-sm hover:shadow-md transition-shadow">
      <button
        type="button"
        onClick={() => navigate(`/candidates/${item.candidate_id}`)}
        className="text-left w-full"
      >
        <p className="font-semibold text-sm text-brand-900 truncate">
          {item.candidate_name || `Candidate #${item.candidate_id}`}
        </p>
        {item.candidate_email && (
          <p className="text-xs text-slate-500 truncate">{item.candidate_email}</p>
        )}
      </button>
      <div className="flex items-center justify-between mt-2 gap-2">
        {item.fit_score != null && (
          <span className="text-xs font-bold text-brand-700">{item.fit_score}</span>
        )}
        <select
          value={item.status}
          onChange={(e) => onStatusChange(item.candidate_id, e.target.value)}
          disabled={readOnly}
          className="text-xs rounded-lg border border-brand-200 px-2 py-1 ml-auto disabled:opacity-60 disabled:cursor-not-allowed"
          onClick={(e) => e.stopPropagation()}
        >
          {PIPELINE_STAGES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>
    </div>
  )
}

export default function ProjectDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { canWrite } = usePermissions()
  const [project, setProject] = useState(null)
  const [pipeline, setPipeline] = useState({})
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [proj, pipe] = await Promise.all([
        getProject(id),
        getProjectPipeline(id),
      ])
      setProject(proj)
      setPipeline(pipe.pipeline || {})
    } catch {
      setProject(null)
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    load()
  }, [load])

  const handleStatusChange = async (candidateId, status) => {
    if (!canWrite) return
    try {
      await updateProjectCandidateStatus(id, candidateId, status)
      await load()
    } catch {
      window.alert('Failed to update status')
    }
  }

  const handleProjectStatus = async (status) => {
    if (!canWrite) return
    try {
      await updateProject(id, { status })
      await load()
    } catch {
      window.alert('Failed to update project')
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-24">
        <Loader2 className="w-8 h-8 text-brand-500 animate-spin" />
      </div>
    )
  }

  if (!project) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center">
        <p className="text-slate-500 mb-4">Project not found.</p>
        <Link to="/projects" className="text-brand-600 font-semibold">Back to projects</Link>
      </div>
    )
  }

  const total = Object.values(pipeline).reduce((n, col) => n + (col?.length || 0), 0)

  return (
    <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {!canWrite && <ViewerReadOnlyBanner />}
      <div className="flex items-center justify-between gap-4 mb-6 flex-wrap">
        <div className="flex items-center gap-3 min-w-0">
          <button
            type="button"
            onClick={() => navigate('/projects')}
            className="p-2 rounded-lg hover:bg-brand-50 text-slate-400"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="w-10 h-10 rounded-2xl bg-brand-50 ring-1 ring-brand-100 flex items-center justify-center shrink-0">
            <FolderKanban className="w-5 h-5 text-brand-600" />
          </div>
          <div className="min-w-0">
            <h1 className="text-2xl font-extrabold text-brand-900 truncate">{project.name}</h1>
            <p className="text-sm text-slate-500 flex items-center gap-2">
              <Users className="w-4 h-4" />
              {total} candidates · {project.status}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={project.status}
            onChange={(e) => handleProjectStatus(e.target.value)}
            disabled={!canWrite}
            className="text-sm rounded-xl border border-brand-200 px-3 py-2 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            <option value="active">Active</option>
            <option value="paused">Paused</option>
            <option value="closed">Closed</option>
            <option value="draft">Draft</option>
          </select>
          {canWrite && (
            <Link
              to="/analyze"
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-brand-600 text-white text-sm font-semibold hover:bg-brand-700"
            >
              <Settings2 className="w-4 h-4" />
              Analyze resumes
            </Link>
          )}
        </div>
      </div>

      {project.description && (
        <p className="text-sm text-slate-600 mb-6 max-w-3xl">{project.description}</p>
      )}

      <div className="flex gap-4 overflow-x-auto pb-4">
        {PIPELINE_STAGES.map((stage) => {
          const items = pipeline[stage] || []
          const style = COLUMN_STYLES[stage] || COLUMN_STYLES.pending
          return (
            <div
              key={stage}
              className="flex-shrink-0 w-72 rounded-2xl ring-1 ring-brand-100 bg-brand-50/30 flex flex-col max-h-[70vh]"
            >
              <div className={`px-4 py-3 border-b rounded-t-2xl flex items-center justify-between ${style.header}`}>
                <span className="text-sm font-bold capitalize">{stage.replace('-', ' ')}</span>
                <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${style.badge}`}>
                  {items.length}
                </span>
              </div>
              <div className="flex-1 overflow-y-auto p-3 space-y-2">
                {items.length === 0 ? (
                  <p className="text-xs text-slate-400 text-center py-6">Empty</p>
                ) : (
                  items.map((item) => (
                    <CandidateCard
                      key={item.id}
                      item={item}
                      onStatusChange={handleStatusChange}
                      readOnly={!canWrite}
                    />
                  ))
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
