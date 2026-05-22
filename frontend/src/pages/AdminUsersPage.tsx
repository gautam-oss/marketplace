import { useState } from 'react'
import { useAdminUsers, useAdminUpdateUser } from '../hooks/useAdmin'
import LoadingSpinner from '../components/LoadingSpinner'
import Pagination from '../components/Pagination'
import { useToast } from '../components/Toast'

export default function AdminUsersPage() {
  const [page, setPage] = useState(1)
  const [q, setQ] = useState('')
  const [role, setRole] = useState<string | undefined>()
  const { data, isLoading } = useAdminUsers(page, 20, role, q || undefined)
  const { mutate: updateUser } = useAdminUpdateUser()
  const toast = useToast()

  const handleToggleActive = (user_id: string, is_active: boolean) => {
    updateUser({ user_id, payload: { is_active: !is_active } }, {
      onSuccess: () => toast(`User ${is_active ? 'deactivated' : 'activated'}`, 'success'),
      onError: () => toast('Failed to update user', 'error'),
    })
  }

  if (isLoading) return <LoadingSpinner className="py-20" size="lg" />

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Users</h1>

      <div className="flex gap-3 mb-6">
        <input type="search" placeholder="Search users..." value={q} onChange={(e) => { setQ(e.target.value); setPage(1) }}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm" />
        <select value={role ?? ''} onChange={(e) => { setRole(e.target.value || undefined); setPage(1) }}
          className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white text-sm">
          <option value="">All roles</option>
          <option value="buyer">Buyer</option>
          <option value="seller">Seller</option>
          <option value="admin">Admin</option>
        </select>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">User</th>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Role</th>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Status</th>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Joined</th>
              <th className="text-right px-4 py-3 text-gray-600 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data?.items.map((u) => (
              <tr key={u.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <p className="font-medium text-gray-900">{u.full_name ?? '—'}</p>
                  <p className="text-gray-500 text-xs">{u.email}</p>
                </td>
                <td className="px-4 py-3 capitalize text-gray-600">{u.role}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${u.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                    {u.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-500">{new Date(u.created_at).toLocaleDateString('en-IN')}</td>
                <td className="px-4 py-3 text-right">
                  <button onClick={() => handleToggleActive(u.id, u.is_active)}
                    className={`text-xs font-medium px-2 py-1 rounded ${u.is_active ? 'text-red-600 hover:bg-red-50' : 'text-green-600 hover:bg-green-50'} transition-colors`}>
                    {u.is_active ? 'Deactivate' : 'Activate'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data && <Pagination page={page} pages={data.pages} total={data.total} onPageChange={setPage} />}
    </div>
  )
}
