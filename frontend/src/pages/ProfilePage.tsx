import { useMe } from '../hooks/useAuth'
import LoadingSpinner from '../components/LoadingSpinner'

export default function ProfilePage() {
  const { data: user, isLoading } = useMe()

  if (isLoading) return <LoadingSpinner className="py-20" size="lg" />

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Profile</h1>
      <div className="bg-white border border-gray-200 rounded-xl p-6">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-16 h-16 rounded-full bg-indigo-100 flex items-center justify-center text-2xl font-bold text-indigo-600">
            {user?.full_name?.[0]?.toUpperCase() ?? user?.email[0].toUpperCase()}
          </div>
          <div>
            <p className="font-semibold text-gray-900">{user?.full_name ?? '—'}</p>
            <p className="text-gray-500 text-sm">{user?.email}</p>
            <span className="inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700 capitalize">
              {user?.role}
            </span>
          </div>
        </div>
        <p className="text-sm text-gray-500">
          Member since {user?.created_at ? new Date(user.created_at).toLocaleDateString('en-IN', { year: 'numeric', month: 'long' }) : '—'}
        </p>
      </div>
    </div>
  )
}
