import { Link } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  PieChart, Pie, Cell, ResponsiveContainer, Legend,
} from 'recharts'
import { useAdminStats } from '../../hooks/useAdmin'
import LoadingSpinner from '../../components/LoadingSpinner'
import PriceDisplay from '../../components/PriceDisplay'

const PIE_COLORS: Record<string, string> = {
  pending: '#F59E0B',
  paid: '#3B82F6',
  processing: '#6366F1',
  shipped: '#8B5CF6',
  delivered: '#10B981',
  cancelled: '#EF4444',
  refunded: '#6B7280',
}

export default function AdminDashboardPage() {
  const { data: stats, isLoading } = useAdminStats()

  if (isLoading) return <LoadingSpinner className="py-20" size="lg" />

  const revenueData = [
    { month: 'Last Month', revenue: stats?.revenue_last_month ?? 0 },
    { month: 'This Month', revenue: stats?.revenue_this_month ?? 0 },
  ]

  const pieData = Object.entries(stats?.orders_by_status ?? {})
    .filter(([, count]) => (count as number) > 0)
    .map(([name, value]) => ({ name, value: value as number }))

  const statCards = [
    { label: 'Total Users', value: stats?.total_users ?? 0, to: '/admin/users', color: 'text-blue-600 bg-blue-50' },
    { label: 'Sellers', value: stats?.total_sellers ?? 0, to: '/admin/users', color: 'text-indigo-600 bg-indigo-50' },
    { label: 'Buyers', value: stats?.total_buyers ?? 0, to: '/admin/users', color: 'text-purple-600 bg-purple-50' },
    { label: 'New This Week', value: stats?.new_users_this_week ?? 0, to: '/admin/users', color: 'text-green-600 bg-green-50' },
    { label: 'Total Products', value: stats?.total_products ?? 0, to: '/admin/products', color: 'text-orange-600 bg-orange-50' },
    { label: 'Active Products', value: stats?.active_products ?? 0, to: '/admin/products', color: 'text-emerald-600 bg-emerald-50' },
    { label: 'Total Orders', value: stats?.total_orders ?? 0, to: '/admin/orders', color: 'text-pink-600 bg-pink-50' },
    { label: 'Revenue This Month', revenue: stats?.revenue_this_month ?? 0, to: '/admin/orders', color: 'text-amber-600 bg-amber-50' },
  ]

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-8">Dashboard</h1>

      {/* Stats grid 2×4 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {statCards.map((c) => (
          <Link key={c.label} to={c.to} className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-sm transition-shadow">
            <p className={`inline-block text-xs font-medium px-2 py-0.5 rounded-full mb-3 ${c.color}`}>{c.label}</p>
            {'revenue' in c ? (
              <PriceDisplay amount={c.revenue!} size="lg" />
            ) : (
              <p className="text-2xl font-bold text-gray-900">{(c.value as number).toLocaleString('en-IN')}</p>
            )}
          </Link>
        ))}
      </div>

      {/* Charts row */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Revenue bar chart */}
        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <h2 className="font-semibold text-gray-900 mb-4">Revenue (₹)</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={revenueData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="month" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} width={55} />
              <Tooltip
                formatter={(v) => [`₹${Number(v).toLocaleString('en-IN')}`, 'Revenue']}
                contentStyle={{ borderRadius: 8, fontSize: 12 }}
              />
              <Bar dataKey="revenue" fill="#6366F1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Orders by status donut */}
        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <h2 className="font-semibold text-gray-900 mb-4">Orders by Status</h2>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={pieData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={85}
                >
                  {pieData.map((entry) => (
                    <Cell key={entry.name} fill={PIE_COLORS[entry.name] ?? '#6B7280'} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} />
                <Legend iconSize={10} iconType="circle" wrapperStyle={{ fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[220px] flex items-center justify-center text-sm text-gray-400">No order data</div>
          )}
        </div>
      </div>
    </div>
  )
}
