import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { SlidersHorizontal, X, ChevronDown, ChevronRight } from 'lucide-react'
import { useProducts } from '../hooks/useProducts'
import { useCategories } from '../hooks/useCategories'
import ProductCard from '../components/ProductCard'
import SkeletonCard from '../components/SkeletonCard'
import Pagination from '../components/Pagination'
import EmptyState from '../components/EmptyState'
import RatingStars from '../components/RatingStars'
import { ShoppingBag } from 'lucide-react'
import type { CategoryResponse } from '../types'

const SORT_OPTIONS = [
  { value: 'newest', label: 'Newest' },
  { value: 'price_asc', label: 'Price: Low to High' },
  { value: 'price_desc', label: 'Price: High to Low' },
  { value: 'rating', label: 'Top Rated' },
]

const RATING_OPTIONS = [4, 3, 2]

function CategoryNode({
  cat,
  selectedId,
  onSelect,
  depth = 0,
}: {
  cat: CategoryResponse
  selectedId: string | undefined
  onSelect: (id: string) => void
  depth?: number
}) {
  const [open, setOpen] = useState(false)
  const hasChildren = (cat.children?.length ?? 0) > 0

  return (
    <div>
      <div
        className={`flex items-center gap-1 py-1.5 px-2 rounded-lg cursor-pointer text-sm transition-colors ${
          selectedId === cat.id ? 'bg-indigo-50 text-indigo-700 font-medium' : 'text-gray-700 hover:bg-gray-50'
        }`}
        style={{ paddingLeft: `${8 + depth * 12}px` }}
      >
        {hasChildren && (
          <button onClick={() => setOpen((o) => !o)} className="text-gray-400 hover:text-gray-600 shrink-0">
            {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>
        )}
        {!hasChildren && <span className="w-4 shrink-0" />}
        <span onClick={() => onSelect(cat.id)} className="flex-1">
          {cat.name}
        </span>
      </div>
      {open && hasChildren && (
        <div>
          {cat.children!.map((child) => (
            <CategoryNode key={child.id} cat={child} selectedId={selectedId} onSelect={onSelect} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  )
}

function Sidebar({
  categories,
  selectedCategory,
  minPrice,
  maxPrice,
  minRating,
  sort,
  onCategoryChange,
  onMinPriceChange,
  onMaxPriceChange,
  onRatingChange,
  onSortChange,
  onClearAll,
}: {
  categories: CategoryResponse[]
  selectedCategory: string | undefined
  minPrice: string
  maxPrice: string
  minRating: string | undefined
  sort: string
  onCategoryChange: (id: string | undefined) => void
  onMinPriceChange: (v: string) => void
  onMaxPriceChange: (v: string) => void
  onRatingChange: (v: string | undefined) => void
  onSortChange: (v: string) => void
  onClearAll: () => void
}) {
  const hasFilters = selectedCategory || minPrice || maxPrice || minRating || sort !== 'newest'

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-900">Filters</h3>
        {hasFilters && (
          <button onClick={onClearAll} className="text-xs text-indigo-600 hover:underline">
            Clear all
          </button>
        )}
      </div>

      {/* Sort */}
      <div>
        <p className="text-sm font-medium text-gray-700 mb-2">Sort by</p>
        <select
          value={sort}
          onChange={(e) => onSortChange(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
        >
          {SORT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      {/* Categories */}
      <div>
        <p className="text-sm font-medium text-gray-700 mb-2">Category</p>
        <div className="space-y-0.5">
          <div
            className={`flex items-center gap-2 py-1.5 px-2 rounded-lg cursor-pointer text-sm transition-colors ${
              !selectedCategory ? 'bg-indigo-50 text-indigo-700 font-medium' : 'text-gray-700 hover:bg-gray-50'
            }`}
            onClick={() => onCategoryChange(undefined)}
          >
            <span className="w-4 shrink-0" />
            All Categories
          </div>
          {categories.map((cat) => (
            <CategoryNode
              key={cat.id}
              cat={cat}
              selectedId={selectedCategory}
              onSelect={(id) => onCategoryChange(selectedCategory === id ? undefined : id)}
            />
          ))}
        </div>
      </div>

      {/* Price range */}
      <div>
        <p className="text-sm font-medium text-gray-700 mb-2">Price range (₹)</p>
        <div className="flex gap-2 items-center">
          <input
            type="number"
            placeholder="Min"
            value={minPrice}
            onChange={(e) => onMinPriceChange(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <span className="text-gray-400 text-sm shrink-0">–</span>
          <input
            type="number"
            placeholder="Max"
            value={maxPrice}
            onChange={(e) => onMaxPriceChange(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
      </div>

      {/* Rating */}
      <div>
        <p className="text-sm font-medium text-gray-700 mb-2">Minimum rating</p>
        <div className="space-y-2">
          {RATING_OPTIONS.map((r) => (
            <label key={r} className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="rating"
                checked={minRating === String(r)}
                onChange={() => onRatingChange(minRating === String(r) ? undefined : String(r))}
                className="accent-indigo-600"
              />
              <RatingStars rating={r} size={14} />
              <span className="text-sm text-gray-600">& up</span>
            </label>
          ))}
        </div>
      </div>
    </div>
  )
}

export default function ProductListPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [showFilters, setShowFilters] = useState(false)
  const [minPriceInput, setMinPriceInput] = useState(searchParams.get('min_price') ?? '')
  const [maxPriceInput, setMaxPriceInput] = useState(searchParams.get('max_price') ?? '')

  const q = searchParams.get('q') ?? ''
  const categoryId = searchParams.get('category') ?? undefined
  const minPrice = searchParams.get('min_price') ? Number(searchParams.get('min_price')) : undefined
  const maxPrice = searchParams.get('max_price') ? Number(searchParams.get('max_price')) : undefined
  const minRating = searchParams.get('min_rating') ?? undefined
  const sort = searchParams.get('sort') ?? 'newest'
  const page = Number(searchParams.get('page') ?? '1')

  const { data: products, isLoading } = useProducts({
    q: q || undefined,
    category: categoryId,
    min_price: minPrice,
    max_price: maxPrice,
    min_rating: minRating ? Number(minRating) : undefined,
    sort,
    page,
    per_page: 20,
  })
  const { data: categories } = useCategories()

  const update = (key: string, value: string | undefined) => {
    const p = new URLSearchParams(searchParams)
    if (value) p.set(key, value)
    else p.delete(key)
    p.delete('page')
    setSearchParams(p)
  }

  const clearAll = () => {
    setMinPriceInput('')
    setMaxPriceInput('')
    setSearchParams(q ? { q } : {})
  }

  const applyPriceRange = () => {
    const p = new URLSearchParams(searchParams)
    if (minPriceInput) p.set('min_price', minPriceInput)
    else p.delete('min_price')
    if (maxPriceInput) p.set('max_price', maxPriceInput)
    else p.delete('max_price')
    p.delete('page')
    setSearchParams(p)
  }

  const sidebarProps = {
    categories: categories ?? [],
    selectedCategory: categoryId,
    minPrice: minPriceInput,
    maxPrice: maxPriceInput,
    minRating,
    sort,
    onCategoryChange: (id: string | undefined) => update('category', id),
    onMinPriceChange: (v: string) => { setMinPriceInput(v); if (!v) update('min_price', undefined) },
    onMaxPriceChange: (v: string) => { setMaxPriceInput(v); if (!v) update('max_price', undefined) },
    onRatingChange: (v: string | undefined) => update('min_rating', v),
    onSortChange: (v: string) => update('sort', v === 'newest' ? undefined : v),
    onClearAll: clearAll,
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header row */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">
            {q ? `Results for "${q}"` : 'All Products'}
          </h1>
          {products && (
            <p className="text-sm text-gray-500 mt-0.5">{products.total} products found</p>
          )}
        </div>
        <button
          onClick={() => setShowFilters(true)}
          className="md:hidden flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium"
        >
          <SlidersHorizontal size={16} />
          Filters
        </button>
      </div>

      <div className="flex gap-8">
        {/* Desktop sidebar */}
        <aside className="hidden md:block w-64 shrink-0">
          <div className="bg-white border border-gray-200 rounded-xl p-5 sticky top-24">
            <Sidebar {...sidebarProps} />
            <button
              onClick={applyPriceRange}
              className="mt-4 w-full py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
            >
              Apply price range
            </button>
          </div>
        </aside>

        {/* Mobile bottom sheet */}
        {showFilters && (
          <div className="fixed inset-0 z-50 md:hidden">
            <div className="absolute inset-0 bg-black/50" onClick={() => setShowFilters(false)} />
            <div className="absolute bottom-0 left-0 right-0 bg-white rounded-t-2xl p-6 max-h-[85vh] overflow-y-auto">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-bold text-gray-900 text-lg">Filters</h3>
                <button onClick={() => setShowFilters(false)}>
                  <X size={20} className="text-gray-500" />
                </button>
              </div>
              <Sidebar {...sidebarProps} />
              <div className="flex gap-3 mt-6">
                <button onClick={() => { clearAll(); setShowFilters(false) }}
                  className="flex-1 py-2 border border-gray-300 rounded-lg text-sm font-medium">
                  Clear all
                </button>
                <button onClick={() => { applyPriceRange(); setShowFilters(false) }}
                  className="flex-1 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors">
                  Apply
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Product grid */}
        <div className="flex-1 min-w-0">
          {isLoading ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {Array.from({ length: 8 }).map((_, i) => <SkeletonCard key={i} />)}
            </div>
          ) : !products?.items.length ? (
            <EmptyState
              icon={<ShoppingBag size={48} />}
              title="No products found"
              description="Try different keywords or remove some filters."
              action={
                <button onClick={clearAll} className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors">
                  Clear filters
                </button>
              }
            />
          ) : (
            <>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {products.items.map((p) => <ProductCard key={p.id} product={p} />)}
              </div>
              <Pagination
                page={page}
                pages={products.pages}
                total={products.total}
                onPageChange={(p) => update('page', String(p))}
              />
            </>
          )}
        </div>
      </div>
    </div>
  )
}
