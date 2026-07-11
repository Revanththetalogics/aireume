import { useState, useEffect } from 'react'
import { Loader2, Shield } from 'lucide-react'
import { getRequisitionSettings, updateRequisitionSettings } from '../../lib/api'
import { Button } from '../ui'
import usePermissions from '../../hooks/usePermissions'

export default function RequisitionSettingsPanel() {
  const { isAdmin } = usePermissions()
  const [settings, setSettings] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [gateMode, setGateMode] = useState('warn')
  const [hmPerm, setHmPerm] = useState('view_only')
  const [resumeWeight, setResumeWeight] = useState(40)
  const [interviewWeight, setInterviewWeight] = useState(60)

  useEffect(() => {
    getRequisitionSettings()
      .then((s) => {
        setSettings(s)
        setGateMode(s.intake_gate_mode || 'warn')
        setHmPerm(s.hm_pipeline_permission || 'view_only')
        const hw = s.hiring_signal_weights || {}
        setResumeWeight(Math.round((hw.resume ?? 0.4) * 100))
        setInterviewWeight(Math.round((hw.interview ?? 0.6) * 100))
      })
      .catch(() => setSettings(null))
      .finally(() => setLoading(false))
  }, [])

  const handleSave = async () => {
    setSaving(true)
    try {
      const updated = await updateRequisitionSettings({
        intake_gate_mode: gateMode,
        hm_pipeline_permission: hmPerm,
        hiring_signal_weights: {
          resume: resumeWeight / 100,
          interview: interviewWeight / 100,
        },
      })
      setSettings(updated)
    } catch {
      window.alert('Failed to save requisition settings')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="w-6 h-6 animate-spin text-brand-500" />
      </div>
    )
  }

  if (!isAdmin) {
    return (
      <p className="text-sm text-slate-500">Only admins can change requisition workflow settings.</p>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-semibold text-slate-700 mb-1">Intake gate before screening</label>
        <p className="text-xs text-slate-500 mb-2">Controls whether recruiters can screen before HM intake is calibrated.</p>
        <select
          value={gateMode}
          onChange={(e) => setGateMode(e.target.value)}
          className="w-full max-w-md rounded-xl border border-brand-200 px-3 py-2 text-sm"
        >
          <option value="warn">Warn — allow with warning</option>
          <option value="block">Block — require calibration</option>
          <option value="optional">Optional — no gate</option>
        </select>
      </div>
      <div>
        <label className="block text-sm font-semibold text-slate-700 mb-1">Hiring manager pipeline access</label>
        <p className="text-xs text-slate-500 mb-2">What HMs can do on requisition pipelines.</p>
        <select
          value={hmPerm}
          onChange={(e) => setHmPerm(e.target.value)}
          className="w-full max-w-md rounded-xl border border-brand-200 px-3 py-2 text-sm"
        >
          <option value="view_only">View only</option>
          <option value="shortlist_reject">Shortlist / reject</option>
          <option value="full">Full pipeline control</option>
        </select>
      </div>
      <div>
        <label className="block text-sm font-semibold text-slate-700 mb-1">Default hiring signal weights</label>
        <p className="text-xs text-slate-500 mb-2">Tenant default for combined score (resume vs interview). Per-requisition overrides in requisition scoring settings.</p>
        <div className="flex flex-wrap items-center gap-4 max-w-md">
          <label className="text-sm">
            Resume %
            <input
              type="number"
              min={0}
              max={100}
              value={resumeWeight}
              onChange={(e) => setResumeWeight(Number(e.target.value))}
              className="mt-1 block w-24 rounded-xl border border-brand-200 px-3 py-2 text-sm"
            />
          </label>
          <label className="text-sm">
            Interview %
            <input
              type="number"
              min={0}
              max={100}
              value={interviewWeight}
              onChange={(e) => setInterviewWeight(Number(e.target.value))}
              className="mt-1 block w-24 rounded-xl border border-brand-200 px-3 py-2 text-sm"
            />
          </label>
        </div>
      </div>
      <Button onClick={handleSave} disabled={saving}>
        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
        Save workflow settings
      </Button>
    </div>
  )
}
