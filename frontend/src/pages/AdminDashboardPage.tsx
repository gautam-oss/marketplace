import { Link } from 'react-router-dom'
import { Users, Package, ShoppingCart, Star } from 'lucide-react'
import { useAdminStats } from '../hooks/useAdmin'
import LoadingSpinner from '../components/LoadingSpinner'
import PriceDisplay from '../components/PriceDisplay'

export default function AdminDashboardPage() {
  const { data: stats, isLoading } = useAdminStats()

  if (isLoading) return <LoadingSpinner className="py-20" size="lg" />

  const cards = [
    { label: 'Total users', value: stats?.total_users ?? 0, icon: <Users size={20} />, to: '/admin/users', color: 'bg-blue-50 text-blue-600' },
    { label: 'Total products', value: stats?.total_products ?? 0, icon: <Package size={20} />, to: '/admin/products', color: 'bg-green-50 text-green-600' },
    { label: 'Total orders', value: stats?.total_orders ?? 0, icon: <ShoppingCart size={20} />, to: '/admin/orders', color: 'bg-purple-50 text-purple-600' },
    { label: 'Active products', value: stats?.active_products ?? 0, icon: <Star size={20} />, to: '/admin/products', color: 'bg-amber-50 text-amber-600' },
  ]

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-8">Admin Dashboard</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {cards.map((c) => (
          <Link key={c.label} to={c.to} className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-sm transition-shadow">
            <div className={`inline-flex p-2 rounded-lg ${c.color} mb-3`}>{c.icon}</div>
            <p className="text-2xl font-bold text-gray-900">{c.value.toLocaleString('en-IN')}</p>
            <p className="text-sm text-gray-500 mt-1">{c.label}</p>
          </Link>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <h2 className="font-semibold text-gray-900 mb-4">Revenue</h2>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">This month</span>
              <PriceDisplay amount={stats?.revenue_this_month ?? 0} size="lg" />
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Last month</span>
              <PriceDisplay amount={stats?.revenue_last_month ?? 0} />
            </div>
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <h2 className="font-semibold text-gray-900 mb-4">Orders by status</h2>
          <div className="space-y-2">
            {Object.entries(stats?.orders_by_status ?? {}).map(([status, count]) => (
              <div key={status} className="flex justify-between items-center text-sm">
                <span className="capitalize text-gray-600">{status}</span>
                <span className="font-medium text-gray-900">{count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
