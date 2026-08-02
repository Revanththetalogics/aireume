import { useState, useEffect, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Briefcase, Loader2, UserPlus, Inbox, ChevronRight } from 'lucide-react'
import {
  listRequisitionOpenRequests,
  assignRequisitionOpenRequest,
  getTeamMembers,
} from '../lib/api'
import { Button, Card } from '../components/ui'
import PageHeaderCard from '../components/patterns/PageHeaderCard'
import usePermissions from '../hooks/usePermissions'
import { REQUISITIONS } from '../lib/uxLabels'
import { showSuccess, showError } from '../lib/toast'

function AssignModal({ request, recruiters, onClose, onAssigned }) {
  const [recruiterId, setRecruiterId] = useState('')
  const [saving, setSaving] = useState(false)

  const handleAssign = async () => {
    if (!recruiterId) return
    setSaving(true)
    try {
      const req = await assignRequisitionOpenRequest(
        request.id,
        Number(recruiterId),
        request.requested_by,
      )
      showSuccess('Recruiter assigned — requisition created')
      onAssigned(req)
      onClose()
    } catch (err) {
      showError(err.response?.data?.detail || 'Assignment failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-2xl ring-1 ring-brand-100 shadow-brand-xl w-full max-w-lg p-6 space-y-4">
        <h3 className="text-lg font-bold text-brand-900">Assign recruiter</h3>
        <p className="text-sm text-slate-600">
          <span className="font-semibold">{request.title}</span>
          {request.requester_email && (
            <> — requested by {request.requester_email}</>
          )}
        </p>
        <label className="block text-sm">
          <span className="font-semibold text-slate-700">Recruiter</span>
          <select
            value={recruiterId}
            onChange={(e) => setRecruiterId(e.target.value)}
            className="mt-1 w-full rounded-xl border border-brand-200 px-3 py-2 text-sm"
          >
            <option value="">Select recruiter…</option>
            {recruiters.map((m) => (
              <option key={m.id} value={m.id}>{m.email}</option>
            ))}
          </select>
        </label>
        <div className="flex gap-2 justify-end">
          <Button variant="ghost" onClick={onClose} disabled={saving}>Cancel</Button>
          <Button onClick={handleAssign} disabled={!recruiterId || saving}>
            {saving ? 'Assigning…' : 'Assign & create requisition'}
          </Button>
        </div>
      </div>
    </div>
  )
}

export default function OpenRequestsPage() {
  const navigate = useNavigate()
  const { canAssign, isHiringManager } = usePermissions()
  const [requests, setRequests] = useState([])
  const [recruiters, setRecruiters] = useState([])
  const [loading, setLoading] = useState(true)
  const [assignTarget, setAssignTarget] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [rows, team] = await Promise.all([
        listRequisitionOpenRequests(),
        canAssign ? getTeamMembers() : Promise.resolve([]),
      ])
      setRequests(Array.isArray(rows) ? rows : [])
      const members = Array.isArray(team) ? team : []
      setRecruiters(members.filter((m) => ['recruiter', 'admin', 'ta_lead'].includes(m.role)))
    } catch {
      setRequests([])
    } finally {
      setLoading(false)
    }
  }, [canAssign])

  useEffect(() => {
    load()
  }, [load])

  if (!canAssign && !isHiringManager) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center text-slate-500">
        You do not have access to opening requests.
      </div>
    )
  }

  const pending = requests.filter((r) => r.status === 'pending')

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeaderCard
        title={REQUISITIONS.openRequestsTitle}
        subtitle={REQUISITIONS.openRequestsSubtitle}
        icon={Inbox}
        actions={
          <Link to="/requisitions" className="text-sm font-semibold text-brand-600 hover:text-brand-800">
            All requisitions
          </Link>
        }
      />

      {loading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="w-8 h-8 animate-spin text-brand-500" />
        </div>
      ) : requests.length === 0 ? (
        <Card className="p-8 text-center text-slate-500">
          <Inbox className="w-10 h-10 mx-auto mb-3 text-brand-200" />
          <p>{REQUISITIONS.openRequestsEmpty}</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {canAssign && pending.length > 0 && (
            <p className="text-sm text-amber-800 bg-amber-50 ring-1 ring-amber-200 rounded-xl px-3 py-2">
              {pending.length} pending opening{pending.length === 1 ? '' : 's'} awaiting recruiter assignment
            </p>
          )}
          {requests.map((r) => (
            <Card key={r.id} className="p-4">
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-bold text-brand-900">{r.title}</h3>
                    <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full ring-1 capitalize bg-slate-50 text-slate-600 ring-slate-200">
                      {r.status}
                    </span>
                  </div>
                  {r.requester_email && (
                    <p className="text-xs text-slate-500 mt-1">Requested by {r.requester_email}</p>
                  )}
                  {r.notes && (
                    <p className="text-sm text-slate-600 mt-2 line-clamp-2">{r.notes}</p>
                  )}
                  <p className="text-xs text-slate-400 mt-1">
                    {r.jd_text?.split(/\s+/).filter(Boolean).length || 0} words in JD
                  </p>
                </div>
                <div className="flex gap-2 shrink-0">
                  {canAssign && r.status === 'pending' && (
                    <Button size="sm" onClick={() => setAssignTarget(r)}>
                      <UserPlus className="w-4 h-4" />
                      Assign recruiter
                    </Button>
                  )}
                  {r.requisition_id && (
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => navigate(`/requisitions/${r.requisition_id}`)}
                    >
                      Open requisition
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {assignTarget && (
        <AssignModal
          request={assignTarget}
          recruiters={recruiters}
          onClose={() => setAssignTarget(null)}
          onAssigned={() => load()}
        />
      )}
    </div>
  )
}
