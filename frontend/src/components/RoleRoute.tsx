import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

interface RoleRouteProps {
  roles: Array<'buyer' | 'seller' | 'admin'>;
}

export default function RoleRoute({ roles }: RoleRouteProps) {
  const { isAuthenticated, user } = useAuthStore()

  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (!user || !roles.includes(user.role)) return <Navigate to="/" replace />

  return <Outlet />
}
