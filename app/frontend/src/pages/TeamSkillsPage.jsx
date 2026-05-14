import { useState, useEffect, useCallback } from 'react'
import { Users, Plus, Trash2, Edit2, X, Loader2, AlertCircle } from 'lucide-react'
import { getTeamProfiles, createTeamProfile, updateTeamProfile, deleteTeamProfile } from '../lib/api'

const PROFICIENCY_LEVELS = ['Basic', 'Intermediate', 'Advanced', 'Expert']

const PROFICIENCY_COLORS = {
  basic: 'bg-slate-100 text-slate-700 ring-slate-200',
  intermediate: 'bg-blue-50 text-blue-700 ring-blue-200',
  advanced: 'bg-brand-50 text-brand-700 ring-brand-200',
  expert: 'bg-amber-50 text-amber-700 ring-amber-200',
}

function ProficiencyChip({ skill, onRemove }) {
  const level = (skill.proficiency || 'intermediate').toLowerCase()
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold ring-1 ${PROFICIENCY_COLORS[level] || PROFICIENCY_COLORS.intermediate}`}
    >
      {skill.skill || skill.name}
      <span className="text-[10px] opacity-70 uppercase tracking-wide">({skill.proficiency || 'Intermediate'})</span>
      {onRemove && (
        <button
          onClick={onRemove}
          className="p-0.5 rounded hover:bg-black/10 transition-colors"
          title="Remove skill"
        >
          <X className="w-3 h-3" />
        </button>
      )}
    </span>
  )
}

function SkillAdder({ skills, onAddSkill, onRemoveSkill }) {
  const [skillName, setSkillName] = useState('')
  const [proficiency, setProficiency] = useState('Intermediate')

  const handleAdd = () => {
    const name = skillName.trim()
    if (!name) return
    onAddSkill({ skill: name, proficiency })
    setSkillName('')
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleAdd()
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-col sm:flex-row gap-2">
        <input
          type="text"
          value={skillName}
          onChange={(e) => setSkillName(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Enter a skill..."
          className="flex-1 px-3 py-2 rounded-xl text-sm bg-slate-50 border border-slate-200
            text-slate-800 placeholder-slate-400
            focus:outline-none focus:ring-2 focus:ring-brand-300 focus:border-brand-300
            transition-all"
        />
        <select
          value={proficiency}
          onChange={(e) => setProficiency(e.target.value)}
          className="px-3 py-2 rounded-xl text-sm bg-slate-50 border border-slate-200 text-slate-700
            focus:outline-none focus:ring-2 focus:ring-brand-300 cursor-pointer"
        >
          {PROFICIENCY_LEVELS.map((level) => (
            <option key={level} value={level}>{level}</option>
          ))}
        </select>
        <button
          onClick={handleAdd}
          disabled={!skillName.trim()}
          className="px-4 py-2 rounded-xl text-xs font-semibold bg-brand-600 text-white
            hover:bg-brand-700 disabled:opacity-40 disabled:cursor-not-allowed
            transition-all flex items-center gap-1.5 shrink-0"
        >
          <Plus className="w-3.5 h-3.5" />
          Add
        </button>
      </div>
      {skills.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {skills.map((skill, i) => (
            <ProficiencyChip
              key={`${skill.skill}-${i}`}
              skill={skill}
              onRemove={() => onRemoveSkill(i)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function ProfileCard({ profile, onEdit, onDelete }) {
  const skills = profile.skills || []
  return (
    <div className="bg-white rounded-2xl p-5 ring-1 ring-slate-200 shadow-brand-sm hover:shadow-brand transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-600 to-brand-400 flex items-center justify-center text-white shadow-brand-sm">
            <Users className="w-4 h-4" />
          </div>
          <h3 className="text-sm font-bold text-slate-800">{profile.team_name}</h3>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => onEdit(profile)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-brand-600 hover:bg-brand-50 transition-colors"
            title="Edit profile"
          >
            <Edit2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => onDelete(profile)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors"
            title="Delete profile"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
      {skills.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {skills.map((skill, i) => (
            <ProficiencyChip key={`${skill.skill}-${i}`} skill={skill} />
          ))}
        </div>
      ) : (
        <p className="text-xs text-slate-400 italic">No skills added yet</p>
      )}
      <p className="text-[10px] text-slate-400 mt-3">
        {skills.length} skill{skills.length !== 1 ? 's' : ''} &middot; Created {new Date(profile.created_at).toLocaleDateString()}
      </p>
    </div>
  )
}

function ProfileModal({ profile, onSave, onClose }) {
  const isEdit = !!profile
  const [teamName, setTeamName] = useState(profile?.team_name || '')
  const [skills, setSkills] = useState(profile?.skills || [])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleAddSkill = useCallback((skill) => {
    setSkills((prev) => [...prev, skill])
  }, [])

  const handleRemoveSkill = useCallback((index) => {
    setSkills((prev) => prev.filter((_, i) => i !== index))
  }, [])

  const handleSave = async () => {
    if (!teamName.trim()) {
      setError('Team name is required')
      return
    }
    setSaving(true)
    setError('')
    try {
      await onSave({ team_name: teamName.trim(), skills })
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to save profile')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white/95 backdrop-blur-xl rounded-3xl ring-1 ring-brand-100 shadow-brand-xl w-full max-w-lg p-6 card-animate">
        <div className="flex items-center justify-between mb-5">
          <h3 className="font-extrabold text-brand-900 tracking-tight">
            {isEdit ? 'Edit Team Profile' : 'New Team Profile'}
          </h3>
          <button onClick={onClose} className="p-1.5 hover:bg-brand-50 rounded-xl transition-colors">
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1.5">Team Name</label>
            <input
              type="text"
              value={teamName}
              onChange={(e) => setTeamName(e.target.value)}
              placeholder="e.g. Backend Engineering"
              className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1.5">Skills</label>
            <SkillAdder
              skills={skills}
              onAddSkill={handleAddSkill}
              onRemoveSkill={handleRemoveSkill}
            />
          </div>

          {error && (
            <p className="text-sm text-red-600 flex items-center gap-2 font-medium">
              <AlertCircle className="w-4 h-4" />{error}
            </p>
          )}

          <div className="flex justify-end gap-2 pt-1">
            <button
              onClick={onClose}
              className="px-4 py-2 ring-1 ring-brand-200 text-sm font-semibold text-brand-700 rounded-xl hover:bg-brand-50 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving || !teamName.trim()}
              className="px-4 py-2 btn-brand text-white text-sm font-bold rounded-xl disabled:opacity-60 shadow-brand-sm flex items-center gap-2"
            >
              {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              {isEdit ? 'Save Changes' : 'Create Profile'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function DeleteConfirmModal({ profile, onConfirm, onClose }) {
  const [deleting, setDeleting] = useState(false)

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await onConfirm()
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white/95 backdrop-blur-xl rounded-3xl ring-1 ring-brand-100 shadow-brand-xl w-full max-w-sm p-6 card-animate">
        <h3 className="font-extrabold text-red-900 tracking-tight mb-2">Delete Team Profile</h3>
        <p className="text-sm text-slate-600 mb-5">
          Are you sure you want to delete <strong>{profile.team_name}</strong>? This action cannot be undone.
        </p>
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 ring-1 ring-slate-200 text-sm font-semibold text-slate-600 rounded-xl hover:bg-slate-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-bold rounded-xl disabled:opacity-60 transition-colors flex items-center gap-2"
          >
            {deleting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            Delete
          </button>
        </div>
      </div>
    </div>
  )
}

export default function TeamSkillsPage() {
  const [profiles, setProfiles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editingProfile, setEditingProfile] = useState(null)   // null = closed, {} = new, existing = edit
  const [deletingProfile, setDeletingProfile] = useState(null)
  const [showCreate, setShowCreate] = useState(false)

  const loadProfiles = useCallback(async () => {
    try {
      setError('')
      const data = await getTeamProfiles()
      setProfiles(Array.isArray(data) ? data : data.profiles || [])
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load team profiles')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadProfiles() }, [loadProfiles])

  const handleCreate = async (data) => {
    await createTeamProfile(data)
    setShowCreate(false)
    await loadProfiles()
  }

  const handleUpdate = async (data) => {
    await updateTeamProfile(editingProfile.id, data)
    setEditingProfile(null)
    await loadProfiles()
  }

  const handleDelete = async () => {
    await deleteTeamProfile(deletingProfile.id)
    setDeletingProfile(null)
    await loadProfiles()
  }

  return (
    <div>
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between card-animate">
          <div>
            <h2 className="text-3xl font-extrabold text-brand-900 tracking-tight">Team Skills</h2>
            <p className="text-slate-500 text-sm mt-1 font-medium">
              Define team skill profiles for skill-aware analysis and gap tracking.
            </p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2.5 btn-brand text-white text-sm font-bold rounded-xl shadow-brand-sm"
          >
            <Plus className="w-4 h-4" /> Add Team
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-center gap-2 px-4 py-3 bg-red-50 ring-1 ring-red-200 rounded-xl text-sm text-red-700 font-medium">
            <AlertCircle className="w-4 h-4 shrink-0" />
            {error}
          </div>
        )}

        {/* Loading */}
        {loading ? (
          <div className="flex justify-center py-16">
            <div className="w-8 h-8 border-4 border-brand-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : profiles.length === 0 ? (
          /* Empty state */
          <div className="bg-white rounded-2xl p-10 ring-1 ring-slate-200 shadow-brand-sm text-center">
            <Users className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <h3 className="text-lg font-bold text-slate-700 mb-1">No team profiles yet</h3>
            <p className="text-sm text-slate-500 mb-5">
              Add your first team to get skill-aware analysis.
            </p>
            <button
              onClick={() => setShowCreate(true)}
              className="inline-flex items-center gap-2 px-5 py-2.5 btn-brand text-white text-sm font-bold rounded-xl shadow-brand-sm"
            >
              <Plus className="w-4 h-4" /> Add Team Profile
            </button>
          </div>
        ) : (
          /* Cards grid */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {profiles.map((profile) => (
              <ProfileCard
                key={profile.id}
                profile={profile}
                onEdit={(p) => setEditingProfile(p)}
                onDelete={(p) => setDeletingProfile(p)}
              />
            ))}
          </div>
        )}
      </main>

      {/* Create Modal */}
      {showCreate && (
        <ProfileModal
          profile={null}
          onSave={handleCreate}
          onClose={() => setShowCreate(false)}
        />
      )}

      {/* Edit Modal */}
      {editingProfile && (
        <ProfileModal
          profile={editingProfile}
          onSave={handleUpdate}
          onClose={() => setEditingProfile(null)}
        />
      )}

      {/* Delete Confirmation */}
      {deletingProfile && (
        <DeleteConfirmModal
          profile={deletingProfile}
          onConfirm={handleDelete}
          onClose={() => setDeletingProfile(null)}
        />
      )}
    </div>
  )
}
