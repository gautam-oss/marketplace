import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import { useProducts } from '../hooks/useProducts'
import { useCategories } from '../hooks/useCategories'
import ProductCard from '../components/ProductCard'
import SkeletonCard from '../components/SkeletonCard'

const CATEGORY_EMOJIS: Record<string, string> = {
  electronics: '💻',
  fashion: '👗',
  home: '🏠',
  beauty: '💄',
  sports: '⚽',
  books: '📚',
  toys: '🧸',
  food: '🍎',
  default: '🛍️',
}

function categoryEmoji(slug: string) {
  for (const [key, emoji] of Object.entries(CATEGORY_EMOJIS)) {
    if (slug.includes(key)) return emoji
  }
  return CATEGORY_EMOJIS.default
}

function ProductRow({ title, sort }: { title: string; sort: string }) {
  const { data, isLoading } = useProducts({ sort, per_page: 8 })
  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-900">{title}</h2>
        <Link to={`/products?sort=${sort}`} className="text-sm text-indigo-600 hover:underline">
          View all
        </Link>
      </div>
      {isLoading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {data?.items.map((p) => <ProductCard key={p.id} product={p} />)}
        </div>
      )}
    </section>
  )
}

export default function HomePage() {
  const [query, setQuery] = useState('')
  const navigate = useNavigate()
  const { data: categories } = useCategories()

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) navigate(`/products?q=${encodeURIComponent(query.trim())}`)
  }

  return (
    <div className="min-h-screen">
      {/* Hero */}
      <section className="bg-gradient-to-br from-indigo-600 to-indigo-800 text-white py-20 px-4">
        <div className="max-w-3xl mx-auto text-center">
          <h1 className="text-4xl md:text-5xl font-bold mb-4">
            Shop Everything, Pay in ₹
          </h1>
          <p className="text-indigo-200 text-lg mb-8">
            India's trusted marketplace — millions of products, verified sellers
          </p>
          <form onSubmit={handleSearch} className="flex gap-2 max-w-xl mx-auto">
            <div className="relative flex-1">
              <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search products, brands..."
                className="w-full pl-10 pr-4 py-3 rounded-xl text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-300 text-sm"
              />
            </div>
            <button
              type="submit"
              className="bg-amber-400 hover:bg-amber-500 text-gray-900 font-semibold px-6 py-3 rounded-xl transition-colors"
            >
              Search
            </button>
          </form>
        </div>
      </section>

      <div className="max-w-7xl mx-auto px-4 py-10 space-y-12">
        {/* Category pills */}
        {categories && categories.length > 0 && (
          <section>
            <h2 className="text-xl font-bold text-gray-900 mb-4">Shop by Category</h2>
            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-3">
              {categories.slice(0, 16).map((cat) => (
                <Link
                  key={cat.id}
                  to={`/products?category=${cat.id}`}
                  className="flex flex-col items-center gap-2 p-3 bg-white border border-gray-200 rounded-xl hover:border-indigo-400 hover:shadow-sm transition-all group"
                >
                  {cat.image_url ? (
                    <img src={cat.image_url} alt={cat.name} className="w-10 h-10 object-contain" />
                  ) : (
                    <span className="text-2xl">{categoryEmoji(cat.slug)}</span>
                  )}
                  <span className="text-xs text-gray-700 text-center font-medium group-hover:text-indigo-600 leading-tight">
                    {cat.name}
                  </span>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* Trending Now */}
        <ProductRow title="Trending Now" sort="rating" />

        {/* New Arrivals */}
        <ProductRow title="New Arrivals" sort="newest" />
      </div>
    </div>
  )
}
