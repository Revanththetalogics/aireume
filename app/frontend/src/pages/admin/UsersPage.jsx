import { useState, useEffect, useCallback } from 'react'
import {
  Search,
  ChevronLeft,
  ChevronRight,
  Loader2,
  AlertTriangle,
  X,
  UserPlus,
  Trash2,
  Shield,
  Users,
  Ban,
  PlayCircle,
  Pencil,
  Send,
  Download,
  Key,
  Mail,
  History,
} from 'lucide-react'
import SlideOutPanel from '../../components/admin/SlideOutPanel'
import {
  getAdminTenants,
  getAdminTenantDetail,
  addUserToTenant,
  removeUserFromTenant,
  extractApiError,
} from '../../lib/api'

/* ── Constants ────────────────────────────────────────── */
const PER_PAGE = 20

const ROLE_OPTIONS = [
  { value: '', label: 'All Roles' },
  { value: 'admin', label: 'Admin' },
  { value: 'recruiter', label: 'Recruiter' },
  { value: 'viewer', label: 'Viewer' },
  { value: 'platform_admin', label: 'Platform Admin' },
]

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'active', label: 'Active' },
  { value: 'inactive', label: 'Inactive' },
]

/* ── Role Badge ────────────────────────────────────────── */
function RoleBadge({ role }) {
  const styles = {
    admin: 'bg-purple-50 text-purple-700 ring-purple-200',
    recruiter: 'bg-blue-50 text-blue-700 ring-blue-200',
    viewer: 'bg-gray-50 text-gray-600 ring-gray-200',
    platform_admin: 'bg-teal-50 text-teal-700 ring-teal-200',
  }
  return (
    <span className={`px-2 py-0.5 rounded-md text-xs font-semibold ring-1 ${styles[role] || styles.viewer}`}>
      {role}
    </span>
  )
}

/* ── Status Badge ──────────────────────────────────────── */
function StatusBadge({ isActive }) {
  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ring-1 ${
      isActive
        ? 'bg-green-50 text-green-700 ring-green-200'
        : 'bg-red-50 text-red-700 ring-red-200'
    }`}>
      {isActive ? 'Active' : 'Inactive'}
    </span>
  )
}

/* ── Toast ─────────────────────────────────────────────── */
function Toast({ message, type = 'success', onDone }) {
  useEffect(() => {
    const t = setTimeout(onDone, 3500)
    return () => clearTimeout(t)
  }, [onDone])

  return (
    <div className={`p-4 rounded-xl ring-1 text-sm ${
      type === 'success' ? 'bg-green-50 text-green-700 ring-green-200' : 'bg-red-50 text-red-700 ring-red-200'
    }`}>
      {message}
    </div>
  )
}

/* ── Add User Modal ───────────────────────────────────── */
function AddUserModal({ tenantId, tenantName, onClose, onAdded }) {
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('recruiter')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!email.trim()) return
    setSaving(true)
    setError('')
    try {
      await addUserToTenant(tenantId, { email: email.trim(), role })
      onAdded()
      onClose()
    } catch (err) {
      setError(extractApiError(err, 'Failed to add user'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl ring-1 ring-gray-200 shadow-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-lg font-bold text-gray-900">Add User</h3>
          <button onClick={onClose} className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>
        <p className="text-sm text-gray-600 mb-4">
          Adding to <span className="font-semibold text-gray-800">{tenantName}</span>
        </p>
        {error && (
          <div className="mb-4 p-3 bg-red-50 rounded-lg ring-1 ring-red-200 text-sm text-red-700">{error}</div>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">Email *</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              placeholder="user@company.com"
              className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">Role</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm"
            >
              <option value="admin">Admin</option>
              <option value="recruiter">Recruiter</option>
              <option value="viewer">Viewer</option>
            </select>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 text-sm font-semibold text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving || !email.trim()}
              className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-sm font-bold rounded-lg disabled:opacity-50 transition-colors"
            >
              {saving ? 'Adding...' : 'Add User'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

/* ── Toggle Switch ─────────────────────────────────────── */
function ToggleSwitch({ checked, onChange }) {
  return (
    <button
      onClick={onChange}
      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 ${
        checked ? 'bg-teal-600' : 'bg-gray-300'
      }`}
    >
      <span
        className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
          checked ? 'translate-x-[18px]' : 'translate-x-1'
        }`}
      />
    </button>
  )
}

/* ── User Slide-Out Panel ─────────────────────────────── */
function UserSlideOut({ user, tenantName, onClose, onAction }) {
  if (!user) return null

  const handleResetPassword = () => {
    if (!confirm(`Send password reset email to ${user.email}?`)) return
    alert('Password reset email placeholder — backend endpoint needed.')
  }

  const handleRemoveFromTenant = () => {
    onAction('remove', user)
    onClose()
  }

  const handleSendInvite = () => {
    if (!confirm(`Send invite email to ${user.email}?`)) return
    alert('Invite email sent placeholder — backend endpoint needed.')
  }

  return (
    <SlideOutPanel
      isOpen={!!user}
      onClose={onClose}
      title={user.email}
    >
      <div className="p-6 space-y-6">
        <div>
          <RoleBadge role={user.role} />
        </div>

        <div className="border-b border-gray-200 pb-6">
          <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-4">Profile</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-gray-500">Email</span>
              <span className="text-sm font-medium text-gray-900">{user.email}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-500">Name</span>
              <span className="text-sm font-medium text-gray-900">{user.name || '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-500">Role</span>
              <span className="text-sm font-medium text-gray-900 capitalize">{user.role}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-500">Tenant</span>
              <span className="text-sm font-medium text-gray-900">{tenantName || '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-500">Status</span>
              <span className="text-sm font-medium text-gray-900">{user.is_active !== false ? 'Active' : 'Inactive'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-500">Last Login</span>
              <span className="text-sm font-medium text-gray-900">
                {user.last_login ? new Date(user.last_login).toLocaleDateString() : '—'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-500">Created</span>
              <span className="text-sm font-medium text-gray-900">
                {user.created_at ? new Date(user.created_at).toLocaleDateString() : '—'}
              </span>
            </div>
          </div>
        </div>

        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-3">Actions</h3>

          <button
            onClick={() => { onAction('change-role', user); onClose() }}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 rounded-lg transition-colors text-left"
          >
            <Shield className="w-4 h-4 text-gray-400" />
            Change Role
          </button>

          <button
            onClick={() => { onAction('toggle-status', user); onClose() }}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 rounded-lg transition-colors text-left"
          >
            {user.is_active !== false ? (
              <><Ban className="w-4 h-4 text-gray-400" /> Deactivate</>
            ) : (
              <><PlayCircle className="w-4 h-4 text-gray-400" /> Reactivate</>
            )}
          </button>

          <button
            onClick={handleResetPassword}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 rounded-lg transition-colors text-left"
          >
            <Key className="w-4 h-4 text-gray-400" />
            Reset Password
          </button>

          <button
            onClick={handleRemoveFromTenant}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg transition-colors text-left"
          >
            <Trash2 className="w-4 h-4" />
            Remove from Tenant
          </button>

          <button
            onClick={handleSendInvite}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 rounded-lg transition-colors text-left"
          >
            <Mail className="w-4 h-4 text-gray-400" />
            Send Invite Email
          </button>

          <div className="border-t border-gray-200 my-3" />

          <div className="px-4 py-3 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <History className="w-4 h-4 text-gray-400" />
              <span className="text-sm font-medium text-gray-700">Activity Log</span>
            </div>
            <p className="text-xs text-gray-500">Coming soon</p>
          </div>
        </div>
      </div>
    </SlideOutPanel>
  )
}

/* ── Change Role Modal ─────────────────────────────────── */
function ChangeRoleModal({ user, tenantId, onClose, onDone }) {
  const [role, setRole] = useState(user.role || 'viewer')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async () => {
    setSaving(true)
    setError('')
    try {
      // Note: Role change endpoint uses addUserToTenant with updated role
      await addUserToTenant(tenantId, { email: user.email, role })
      onDone()
      onClose()
    } catch (err) {
      setError(extractApiError(err, 'Failed to change role'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl ring-1 ring-gray-200 shadow-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-lg font-bold text-gray-900">Change Role</h3>
          <button onClick={onClose} className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>
        <p className="text-sm text-gray-600 mb-4">
          Change role for <span className="font-semibold text-gray-800">{user.email}</span>
        </p>
        {error && (
          <div className="mb-4 p-3 bg-red-50 rounded-lg ring-1 ring-red-200 text-sm text-red-700">{error}</div>
        )}
        <div className="space-y-2 mb-6">
          {['admin', 'recruiter', 'viewer'].map(r => (
            <label
              key={r}
              className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                role === r
                  ? 'bg-teal-50 border-teal-300'
                  : 'bg-white border-gray-200 hover:bg-gray-50'
              }`}
            >
              <input
                type="radio"
                name="role"
                value={r}
                checked={role === r}
                onChange={(e) => setRole(e.target.value)}
                className="w-4 h-4 text-teal-600"
              />
              <span className="text-sm font-semibold text-gray-800 capitalize">{r}</span>
            </label>
          ))}
        </div>
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 text-sm font-semibold text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={saving}
            className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-sm font-bold rounded-lg disabled:opacity-50 transition-colors"
          >
            {saving ? 'Saving...' : 'Change Role'}
          </button>
        </div>
      </div>
    </div>
  )
}

/* ── Main UsersPage ────────────────────────────────────── */
export default function UsersPage() {
  // Data
  const [tenants, setTenants] = useState([])
  const [selectedTenantId, setSelectedTenantId] = useState('')
  const [users, setUsers] = useState([])
  const [loadingTenants, setLoadingTenants] = useState(true)
  const [loadingUsers, setLoadingUsers] = useState(false)
  const [error, setError] = useState('')
  const [toast, setToast] = useState(null)

  // Filters
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  // Pagination
  const [page, setPage] = useState(1)

  // Modals
  const [showAddUser, setShowAddUser] = useState(false)
  const [changeRoleUser, setChangeRoleUser] = useState(null)
  const [changeRoleTenantId, setChangeRoleTenantId] = useState(null)
  const [slideOutUser, setSlideOutUser] = useState(null)

  /* ── Fetch tenants ──────────────────────────────────── */
  const fetchTenants = useCallback(async () => {
    setLoadingTenants(true)
    setError('')
    try {
      const data = await getAdminTenants({ per_page: 100 })
      const items = data.tenants || data.items || data || []
      setTenants(items)
    } catch (err) {
      setError(extractApiError(err, 'Failed to load tenants'))
    } finally {
      setLoadingTenants(false)
    }
  }, [])

  useEffect(() => {
    fetchTenants()
  }, [fetchTenants])

  /* ── Fetch users for selected tenant ────────────────── */
  const fetchUsers = useCallback(async () => {
    if (!selectedTenantId) {
      setUsers([])
      return
    }
    setLoadingUsers(true)
    setError('')
    try {
      const detail = await getAdminTenantDetail(selectedTenantId)
      setUsers(detail.users || [])
    } catch (err) {
      setError(extractApiError(err, 'Failed to load users'))
    } finally {
      setLoadingUsers(false)
    }
  }, [selectedTenantId])

  useEffect(() => {
    fetchUsers()
  }, [fetchUsers])

  // Reset page when filters change
  useEffect(() => {
    setPage(1)
  }, [search, roleFilter, statusFilter, selectedTenantId])

  /* ── Get tenant name ────────────────────────────────── */
  const selectedTenant = tenants.find(t => t.id === Number(selectedTenantId))

  /* ── Filtered + paginated users ─────────────────────── */
  const filteredUsers = users.filter(u => {
    if (search && !u.email?.toLowerCase().includes(search.toLowerCase()) && !(u.name || '').toLowerCase().includes(search.toLowerCase())) return false
    if (roleFilter && u.role !== roleFilter) return false
    if (statusFilter === 'active' && u.is_active === false) return false
    if (statusFilter === 'inactive' && u.is_active !== false) return false
    return true
  })

  const totalPages = Math.max(1, Math.ceil(filteredUsers.length / PER_PAGE))
  const paginatedUsers = filteredUsers.slice((page - 1) * PER_PAGE, page * PER_PAGE)

  /* ── Row action handler ─────────────────────────────── */
  const handleRowAction = async (action, user, tenantId) => {
    switch (action) {
      case 'remove':
        if (!confirm(`Remove ${user.email} from this tenant?`)) return
        try {
          await removeUserFromTenant(tenantId, user.id)
          setToast({ message: `${user.email} removed from tenant.`, type: 'success' })
          fetchUsers()
        } catch (err) {
          setToast({ message: extractApiError(err, 'Failed to remove user'), type: 'error' })
        }
        break
      case 'toggle-status':
        setToast({ message: 'User status change requires a dedicated backend endpoint.', type: 'error' })
        break
      case 'change-role':
        setChangeRoleUser(user)
        setChangeRoleTenantId(tenantId)
        break
    }
  }

  /* ── Search handler ─────────────────────────────────── */
  const handleSearchSubmit = (e) => {
    e.preventDefault()
    setSearch(searchInput)
    setPage(1)
  }

  const hasActiveFilters = search || roleFilter || statusFilter

  /* ── Loading skeletons ──────────────────────────────── */
  if (loadingTenants) {
    return (
      <div className="space-y-5">
        <div className="h-8 w-48 bg-gray-200 rounded-lg animate-pulse" />
        <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex gap-4">
              <div className="h-4 w-48 bg-gray-100 rounded animate-pulse" />
              <div className="h-4 w-24 bg-gray-100 rounded animate-pulse" />
              <div className="h-4 w-20 bg-gray-100 rounded animate-pulse" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Users</h1>
          <p className="text-sm text-gray-500 mt-0.5">Cross-tenant user management</p>
        </div>
        {selectedTenantId && (
          <button
            onClick={() => setShowAddUser(true)}
            className="flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-sm font-bold rounded-lg transition-colors"
          >
            <UserPlus className="w-4 h-4" />
            Add User
          </button>
        )}
      </div>

      {toast && <Toast message={toast.message} type={toast.type} onDone={() => setToast(null)} />}

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 rounded-xl ring-1 ring-red-200 text-sm text-red-700 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
          <button onClick={() => selectedTenantId ? fetchUsers() : fetchTenants()} className="ml-auto px-3 py-1 text-xs font-bold bg-red-100 hover:bg-red-200 rounded-lg transition-colors">
            Retry
          </button>
        </div>
      )}

      {/* Tenant selector */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <label className="block text-sm font-semibold text-gray-700 mb-2">Select Tenant</label>
        <select
          value={selectedTenantId}
          onChange={(e) => setSelectedTenantId(e.target.value)}
          className="w-full max-w-md px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm"
        >
          <option value="">Choose a tenant...</option>
          {tenants.map(t => (
            <option key={t.id} value={t.id}>{t.name} ({t.slug})</option>
          ))}
        </select>
      </div>

      {/* Filters (only show when tenant is selected) */}
      {selectedTenantId && (
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="flex flex-wrap items-end gap-3">
            {/* Search */}
            <form onSubmit={handleSearchSubmit} className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  placeholder="Search by email or name..."
                  className="w-full pl-10 pr-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm"
                />
              </div>
            </form>

            {/* Role */}
            <div className="min-w-[140px]">
              <select
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm"
              >
                {ROLE_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>

            {/* Status */}
            <div className="min-w-[140px]">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm"
              >
                {STATUS_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>

            {/* Clear filters */}
            {hasActiveFilters && (
              <button
                onClick={() => { setSearch(''); setSearchInput(''); setRoleFilter(''); setStatusFilter(''); setPage(1) }}
                className="px-3 py-2 text-sm font-medium text-teal-600 hover:text-teal-700 transition-colors"
              >
                Clear filters
              </button>
            )}
          </div>
        </div>
      )}

      {/* Users table */}
      {selectedTenantId && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          {loadingUsers ? (
            <div className="p-6 space-y-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="flex gap-4">
                  <div className="h-4 w-48 bg-gray-100 rounded animate-pulse" />
                  <div className="h-4 w-24 bg-gray-100 rounded animate-pulse" />
                  <div className="h-4 w-20 bg-gray-100 rounded animate-pulse" />
                  <div className="h-4 w-32 bg-gray-100 rounded animate-pulse" />
                </div>
              ))}
            </div>
          ) : paginatedUsers.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-gray-400">
              <Users className="w-12 h-12 mb-3 text-gray-300" />
              <p className="text-sm font-medium">{users.length === 0 ? 'No users in this tenant' : 'No users match your filters'}</p>
              <p className="text-xs mt-1">{users.length === 0 ? 'Add a user to get started' : 'Try adjusting your search or filters'}</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Email</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Name</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Role</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Last Login</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {paginatedUsers.map(user => (
                    <tr key={user.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3">
                        <button
                          onClick={() => setSlideOutUser(user)}
                          className="text-sm text-gray-900 font-medium hover:text-teal-600 transition-colors text-left"
                        >
                          {user.email}
                        </button>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">{user.name || '—'}</td>
                      <td className="px-4 py-3">
                        <RoleBadge role={user.role} />
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge isActive={user.is_active !== false} />
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {user.last_login ? new Date(user.last_login).toLocaleDateString() : '—'}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <ToggleSwitch
                            checked={user.is_active !== false}
                            onChange={() => handleRowAction('toggle-status', user, Number(selectedTenantId))}
                          />
                          <button
                            onClick={() => handleRowAction('change-role', user, Number(selectedTenantId))}
                            className="p-1.5 text-gray-400 hover:text-teal-600 transition-colors"
                            title="Change Role"
                          >
                            <Pencil className="w-5 h-5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {!loadingUsers && filteredUsers.length > PER_PAGE && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gray-50">
              <p className="text-sm text-gray-500">
                Showing {((page - 1) * PER_PAGE) + 1}–{Math.min(page * PER_PAGE, filteredUsers.length)} of {filteredUsers.length}
              </p>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="p-2 rounded-lg border border-gray-300 hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronLeft className="w-4 h-4 text-gray-600" />
                </button>
                <span className="px-3 text-sm text-gray-600">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="p-2 rounded-lg border border-gray-300 hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronRight className="w-4 h-4 text-gray-600" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* No tenant selected prompt */}
      {!selectedTenantId && !loadingTenants && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <Users className="w-10 h-10 text-gray-300 mx-auto mb-2" />
          <p className="text-sm text-gray-500">Select a tenant above to manage its users.</p>
        </div>
      )}

      {/* Modals */}
      {showAddUser && selectedTenantId && (
        <AddUserModal
          tenantId={Number(selectedTenantId)}
          tenantName={selectedTenant?.name || `Tenant #${selectedTenantId}`}
          onClose={() => setShowAddUser(false)}
          onAdded={fetchUsers}
        />
      )}
      {changeRoleUser && (
        <ChangeRoleModal
          user={changeRoleUser}
          tenantId={changeRoleTenantId}
          onClose={() => { setChangeRoleUser(null); setChangeRoleTenantId(null) }}
          onDone={fetchUsers}
        />
      )}
      <UserSlideOut
        user={slideOutUser}
        tenantName={selectedTenant?.name}
        onClose={() => setSlideOutUser(null)}
        onAction={(action, user) => handleRowAction(action, user, Number(selectedTenantId))}
      />
    </div>
  )
}
