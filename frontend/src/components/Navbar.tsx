import { Link, useNavigate } from 'react-router-dom'
import { ShoppingCart, Store, LogOut, User, LayoutDashboard, Shield } from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import { useCartStore } from '../store/cartStore'
import { useNotificationStore } from '../store/notificationStore'
import { useWebSocket } from '../hooks/useWebSocket'
import NotificationBell from './NotificationBell'
import { useQueryClient } from '@tanstack/react-query'

export default function Navbar() {
  const { user, isAuthenticated, logout } = useAuthStore()
  const { cart, clearCart } = useCartStore()
  const clearNotifications = useNotificationStore((s) => s.clear)
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  useWebSocket()

  const handleLogout = () => {
    logout()
    clearCart()
    clearNotifications()
    queryClient.clear()
    navigate('/login')
  }

  const itemCount = cart?.item_count ?? 0

  return (
    <nav className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2 text-indigo-600 font-bold text-xl">
            <Store size={24} />
            Marketplace
          </Link>

          <div className="flex items-center gap-4">
            <Link to="/" className="text-gray-600 hover:text-gray-900 text-sm font-medium">
              Browse
            </Link>

            {isAuthenticated && user ? (
              <>
                {user.role === 'seller' && (
                  <Link
                    to="/seller/dashboard"
                    className="text-gray-600 hover:text-gray-900 text-sm font-medium flex items-center gap-1"
                  >
                    <LayoutDashboard size={16} />
                    Dashboard
                  </Link>
                )}
                {user.role === 'admin' && (
                  <Link
                    to="/admin"
                    className="text-gray-600 hover:text-gray-900 text-sm font-medium flex items-center gap-1"
                  >
                    <Shield size={16} />
                    Admin
                  </Link>
                )}

                <NotificationBell />

                <Link to="/cart" className="relative text-gray-600 hover:text-gray-900">
                  <ShoppingCart size={22} />
                  {itemCount > 0 && (
                    <span className="absolute -top-2 -right-2 bg-indigo-600 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                      {itemCount}
                    </span>
                  )}
                </Link>

                <Link
                  to="/orders"
                  className="text-gray-600 hover:text-gray-900 text-sm font-medium flex items-center gap-1"
                >
                  <User size={16} />
                  {user.full_name?.split(' ')[0] ?? user.email.split('@')[0]}
                </Link>

                <button
                  onClick={handleLogout}
                  className="text-gray-600 hover:text-red-600 transition-colors"
                  title="Logout"
                >
                  <LogOut size={18} />
                </button>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  className="text-gray-600 hover:text-gray-900 text-sm font-medium"
                >
                  Login
                </Link>
                <Link
                  to="/register"
                  className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
                >
                  Sign Up
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
