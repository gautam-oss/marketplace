import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { LayoutDashboard, Users, Package, ShoppingCart, Star, Menu, X, Store } from 'lucide-react'

const NAV = [
  { to: '/admin', label: 'Dashboard', icon: <LayoutDashboard size={18} />, end: true },
  { to: '/admin/users', label: 'Users', icon: <Users size={18} /> },
  { to: '/admin/products', label: 'Products', icon: <Package size={18} /> },
  { to: '/admin/orders', label: 'Orders', icon: <ShoppingCart size={18} /> },
  { to: '/admin/reviews', label: 'Reviews', icon: <Star size={18} /> },
]

function Sidebar({ onClose }: { onClose?: () => void }) {
  return (
    <nav className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-4 py-5 border-b border-gray-100">
        <Store size={20} className="text-indigo-600 shrink-0" />
        <span className="font-bold text-gray-900 text-sm">Admin Panel</span>
      </div>
      <div className="flex-1 p-3 space-y-0.5">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={onClose}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-indigo-50 text-indigo-700'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`
            }
          >
            {item.icon}
            {item.label}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}

export default function AdminLayout() {
  const [open, setOpen] = useState(false)

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Desktop sidebar */}
      <aside className="hidden md:flex w-52 shrink-0 bg-white border-r border-gray-200 flex-col">
        <Sidebar />
      </aside>

      {/* Mobile overlay sidebar */}
      {open && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />
          <aside className="relative w-52 h-full bg-white shadow-xl">
            <button
              onClick={() => setOpen(false)}
              className="absolute top-3 right-3 text-gray-400 hover:text-gray-700"
            >
              <X size={18} />
            </button>
            <Sidebar onClose={() => setOpen(false)} />
          </aside>
        </div>
      )}

      <div className="flex-1 min-w-0 flex flex-col">
        {/* Mobile header */}
        <div className="flex md:hidden items-center gap-3 px-4 py-3 bg-white border-b border-gray-200">
          <button onClick={() => setOpen(true)} className="text-gray-600 hover:text-gray-900">
            <Menu size={20} />
          </button>
          <span className="font-semibold text-gray-900 text-sm">Admin Panel</span>
        </div>
        <div className="flex-1">
          <Outlet />
        </div>
      </div>
    </div>
  )
}
