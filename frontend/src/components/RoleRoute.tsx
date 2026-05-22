import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

interface RoleRouteProps {
  roles: Array<'buyer' | 'seller' | 'admin'>;
}

export default function RoleRoute({ roles }: RoleRouteProps) {
  const { isAuthenticated, user } = useAuthStore()
  const location = useLocation()

  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location.pathname }} replace />
  if (!user || !roles.includes(user.role)) return <Navigate to="/" replace />

  return <Outlet />
}
