import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { ShoppingCart, Zap, ChevronRight, ThumbsUp, BadgeCheck } from 'lucide-react'
import { useProduct } from '../hooks/useProducts'
import { useAddToCart } from '../hooks/useCart'
import { useProductReviews, useCreateReview, useMarkReviewHelpful } from '../hooks/useReviews'
import { useAuthStore } from '../store/authStore'
import { useToast } from '../components/Toast'
import RatingStars from '../components/RatingStars'
import PriceDisplay from '../components/PriceDisplay'
import LoadingSpinner from '../components/LoadingSpinner'

function RatingSummaryBars({
  average,
  total,
  breakdown,
}: {
  average: number
  total: number
  breakdown: Record<number, number>
}) {
  return (
    <div className="flex gap-6">
      <div className="text-center shrink-0">
        <p className="text-5xl font-bold text-gray-900">{average.toFixed(1)}</p>
        <RatingStars rating={average} size={16} />
        <p className="text-sm text-gray-500 mt-1">{total} reviews</p>
      </div>
      <div className="flex-1 space-y-1.5">
        {[5, 4, 3, 2, 1].map((star) => {
          const count = breakdown[star] ?? 0
          const pct = total > 0 ? (count / total) * 100 : 0
          return (
            <div key={star} className="flex items-center gap-2 text-sm">
              <span className="text-gray-500 shrink-0 w-4">{star}</span>
              <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-amber-400 rounded-full transition-all"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-gray-500 shrink-0 w-6 text-right">{count}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function ReviewCard({
  review,
  currentUserId,
}: {
  review: { id: string; user: { id: string; full_name: string | null; avatar_url: string | null }; rating: number; title: string | null; body: string | null; is_verified_purchase: boolean; helpful_count: number; created_at: string }
  currentUserId?: string
}) {
  const { mutate: markHelpful, isPending } = useMarkReviewHelpful()
  const toast = useToast()

  const initials = review.user?.full_name
    ? review.user.full_name.split(' ').map((n) => n[0]).join('').slice(0, 2).toUpperCase()
    : '?'

  const handleHelpful = () => {
    if (!currentUserId) { toast('Please login to mark as helpful', 'info'); return }
    markHelpful(review.id, {
      onError: () => toast('Already marked or cannot mark own review', 'error'),
    })
  }

  return (
    <div className="border-b border-gray-100 py-5 last:border-0">
      <div className="flex items-start gap-3 mb-2">
        <div className="w-9 h-9 rounded-full bg-indigo-100 flex items-center justify-center text-sm font-bold text-indigo-600 shrink-0">
          {initials}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-gray-900 text-sm">
              {review.user?.full_name ?? 'Anonymous'}
            </span>
            {review.is_verified_purchase && (
              <span className="flex items-center gap-1 text-xs text-green-700 bg-green-50 px-2 py-0.5 rounded-full">
                <BadgeCheck size={11} />
                Verified Purchase
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            <RatingStars rating={review.rating} size={13} />
            <span className="text-xs text-gray-400">
              {new Date(review.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
            </span>
          </div>
        </div>
      </div>
      {review.title && <p className="font-medium text-gray-900 mb-1 text-sm">{review.title}</p>}
      {review.body && <p className="text-gray-600 text-sm leading-relaxed">{review.body}</p>}
      <button
        onClick={handleHelpful}
        disabled={isPending}
        className="flex items-center gap-1.5 mt-3 text-xs text-gray-500 hover:text-gray-700 transition-colors"
      >
        <ThumbsUp size={13} />
        Helpful ({review.helpful_count})
      </button>
    </div>
  )
}

function WriteReviewForm({ productId, onSuccess }: { productId: string; onSuccess: () => void }) {
  const [rating, setRating] = useState(0)
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const { mutate: createReview, isPending } = useCreateReview(productId)
  const toast = useToast()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!rating) { toast('Please select a rating', 'info'); return }
    createReview({ rating, title: title || undefined, body: body || undefined }, {
      onSuccess: () => { toast('Review submitted!', 'success'); onSuccess() },
      onError: () => toast('Failed to submit review', 'error'),
    })
  }

  return (
    <form onSubmit={handleSubmit} className="border border-gray-200 rounded-xl p-5 bg-gray-50">
      <h4 className="font-semibold text-gray-900 mb-4">Write a Review</h4>
      <div className="mb-4">
        <p className="text-sm text-gray-600 mb-2">Your rating</p>
        <RatingStars rating={rating} size={28} interactive onChange={setRating} />
      </div>
      <div className="mb-3">
        <input
          type="text"
          placeholder="Title (optional)"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>
      <div className="mb-4">
        <textarea
          rows={4}
          placeholder="Share your experience with this product..."
          value={body}
          onChange={(e) => setBody(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
        />
      </div>
      <button
        type="submit"
        disabled={isPending || !rating}
        className="bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors flex items-center gap-2"
      >
        {isPending && <LoadingSpinner size="sm" />}
        Submit review
      </button>
    </form>
  )
}

export default function ProductDetailPage() {
  const { slug } = useParams<{ slug: string }>()
  const navigate = useNavigate()
  const { data: product, isLoading, error } = useProduct(slug!)
  const { mutate: addToCart, isPending: addingToCart } = useAddToCart()
  const { user, isAuthenticated } = useAuthStore()
  const toast = useToast()

  const [qty, setQty] = useState(1)
  const [activeImage, setActiveImage] = useState(0)
  const [added, setAdded] = useState(false)
  const [reviewPage, setReviewPage] = useState(1)
  const [showReviewForm, setShowReviewForm] = useState(false)

  const { data: reviewData } = useProductReviews(product?.id ?? '', reviewPage)

  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8 animate-pulse">
        <div className="grid md:grid-cols-2 gap-8">
          <div className="bg-gray-100 rounded-xl aspect-square" />
          <div className="space-y-4">
            <div className="h-8 bg-gray-100 rounded w-3/4" />
            <div className="h-6 bg-gray-100 rounded w-1/4" />
            <div className="h-24 bg-gray-100 rounded" />
          </div>
        </div>
      </div>
    )
  }

  if (error || !product) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-20 text-center">
        <p className="text-gray-500">Product not found.</p>
        <button onClick={() => navigate('/')} className="mt-4 text-indigo-600 hover:underline text-sm">
          Back to browse
        </button>
      </div>
    )
  }

  const discountPct =
    product.compare_at_price && product.compare_at_price > product.price
      ? Math.round(((Number(product.compare_at_price) - product.price) / Number(product.compare_at_price)) * 100)
      : 0

  const handleAddToCart = () => {
    if (!isAuthenticated) { navigate('/login'); return }
    addToCart({ product_id: product.id, quantity: qty }, {
      onSuccess: () => { setAdded(true); setTimeout(() => setAdded(false), 2000); toast('Added to cart!', 'success') },
      onError: () => toast('Failed to add to cart', 'error'),
    })
  }

  const handleBuyNow = () => {
    if (!isAuthenticated) { navigate('/login'); return }
    addToCart({ product_id: product.id, quantity: qty }, {
      onSuccess: () => navigate('/checkout'),
      onError: () => toast('Failed to add to cart', 'error'),
    })
  }

  const canReview = isAuthenticated && user?.role === 'buyer'
  const hasReviewed = reviewData?.reviews.items.some((r) => r.user?.id === user?.id)
  const totalReviews = reviewData?.reviews.total ?? 0

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1 text-sm text-gray-500 mb-6 flex-wrap">
        <Link to="/" className="hover:text-gray-900">Home</Link>
        <ChevronRight size={14} />
        {product.category && (
          <>
            <Link to={`/products?category=${product.category.id}`} className="hover:text-gray-900">
              {product.category.name}
            </Link>
            <ChevronRight size={14} />
          </>
        )}
        <span className="text-gray-900 truncate max-w-xs">{product.title}</span>
      </nav>

      <div className="grid md:grid-cols-2 gap-8 mb-12">
        {/* Image gallery */}
        <div>
          <div className="relative bg-gray-100 rounded-xl overflow-hidden aspect-square mb-3">
            {product.images?.[activeImage] ? (
              <img
                src={product.images[activeImage]}
                alt={product.title}
                className="w-full h-full object-contain"
              />
            ) : (
              <span className="absolute inset-0 flex items-center justify-center text-8xl select-none">🛍️</span>
            )}
            {product.images?.length > 1 && (
              <span className="absolute bottom-2 right-2 bg-black/50 text-white text-xs px-2 py-1 rounded-full">
                {activeImage + 1} / {product.images.length}
              </span>
            )}
          </div>
          {product.images?.length > 1 && (
            <div className="flex gap-2 overflow-x-auto pb-1">
              {product.images.map((img, i) => (
                <button
                  key={i}
                  onClick={() => setActiveImage(i)}
                  className={`w-16 h-16 shrink-0 rounded-lg overflow-hidden border-2 transition-colors ${
                    i === activeImage ? 'border-indigo-600' : 'border-transparent'
                  }`}
                >
                  <img src={img} alt="" className="w-full h-full object-cover" />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Product details */}
        <div className="flex flex-col">
          <h1 className="text-2xl font-bold text-gray-900 leading-tight">{product.title}</h1>

          <p className="text-sm text-gray-500 mt-1">
            by{' '}
            <Link to={`/products?seller=${product.seller?.id}`} className="text-indigo-600 hover:underline">
              {product.seller?.full_name ?? 'Seller'}
            </Link>
          </p>

          {product.review_count > 0 && (
            <div className="flex items-center gap-2 mt-2">
              <RatingStars rating={product.average_rating} size={16} showValue />
              <a href="#reviews" className="text-sm text-indigo-600 hover:underline">
                ({product.review_count} reviews)
              </a>
            </div>
          )}

          <div className="flex items-baseline gap-3 mt-4">
            <PriceDisplay amount={product.price} size="xl" />
            {product.compare_at_price && product.compare_at_price > product.price && (
              <>
                <span className="text-gray-400 line-through text-sm">
                  ₹{Number(product.compare_at_price).toLocaleString('en-IN')}
                </span>
                <span className="bg-green-100 text-green-700 text-xs font-bold px-2 py-0.5 rounded">
                  {discountPct}% OFF
                </span>
              </>
            )}
          </div>

          <div className="mt-3">
            {product.stock > 10 ? (
              <span className="text-green-600 text-sm font-medium">In Stock</span>
            ) : product.stock > 0 ? (
              <span className="text-amber-600 text-sm font-medium">Only {product.stock} left!</span>
            ) : (
              <span className="text-red-500 text-sm font-medium">Out of Stock</span>
            )}
          </div>

          {product.description && (
            <p className="text-gray-600 mt-4 leading-relaxed text-sm whitespace-pre-wrap">
              {product.description}
            </p>
          )}

          {product.tags && product.tags.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-4">
              {product.tags.map((tag: string) => (
                <span key={tag} className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full">
                  {tag}
                </span>
              ))}
            </div>
          )}

          {product.stock > 0 && (
            <div className="mt-6 space-y-3">
              <div className="flex items-center gap-3">
                <div className="flex items-center border border-gray-300 rounded-lg">
                  <button onClick={() => setQty((q) => Math.max(1, q - 1))} className="px-3 py-2 text-gray-600 hover:bg-gray-50 rounded-l-lg">−</button>
                  <span className="px-4 py-2 text-sm font-medium min-w-[2.5rem] text-center">{qty}</span>
                  <button onClick={() => setQty((q) => Math.min(Math.min(product.stock, 10), q + 1))} className="px-3 py-2 text-gray-600 hover:bg-gray-50 rounded-r-lg">+</button>
                </div>
                <span className="text-xs text-gray-400">(max 10)</span>
              </div>
              <button
                onClick={handleAddToCart}
                disabled={addingToCart}
                className="w-full flex items-center justify-center gap-2 border-2 border-indigo-600 text-indigo-600 py-2.5 rounded-xl font-semibold hover:bg-indigo-50 disabled:opacity-50 transition-colors"
              >
                {addingToCart ? <LoadingSpinner size="sm" /> : <ShoppingCart size={18} />}
                {added ? 'Added to cart!' : 'Add to Cart'}
              </button>
              <button
                onClick={handleBuyNow}
                className="w-full flex items-center justify-center gap-2 bg-indigo-600 text-white py-2.5 rounded-xl font-semibold hover:bg-indigo-700 transition-colors"
              >
                <Zap size={18} />
                Buy Now
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Reviews */}
      <section id="reviews">
        <h2 className="text-xl font-bold text-gray-900 mb-6">
          Customer Reviews {totalReviews > 0 && `(${totalReviews})`}
        </h2>

        {reviewData?.rating_summary && reviewData.rating_summary.total > 0 && (
          <div className="mb-8">
            <RatingSummaryBars
              average={reviewData.rating_summary.average}
              total={reviewData.rating_summary.total}
              breakdown={reviewData.rating_summary.breakdown}
            />
          </div>
        )}

        {canReview && !hasReviewed && (
          <div className="mb-8">
            {showReviewForm ? (
              <WriteReviewForm
                productId={product.id}
                onSuccess={() => setShowReviewForm(false)}
              />
            ) : (
              <button
                onClick={() => setShowReviewForm(true)}
                className="border border-indigo-600 text-indigo-600 px-5 py-2 rounded-lg text-sm font-medium hover:bg-indigo-50 transition-colors"
              >
                Write a Review
              </button>
            )}
          </div>
        )}

        {reviewData?.reviews.items.length === 0 ? (
          <p className="text-gray-500 text-sm py-8 text-center">
            No reviews yet.{canReview && !hasReviewed && ' Be the first to review!'}
          </p>
        ) : (
          <div className="bg-white border border-gray-200 rounded-xl px-5">
            {reviewData?.reviews.items.map((r) => (
              <ReviewCard key={r.id} review={r} currentUserId={user?.id} />
            ))}
          </div>
        )}

        {(reviewData?.reviews.pages ?? 0) > 1 && (
          <div className="flex justify-center gap-2 mt-6">
            <button
              onClick={() => setReviewPage((p) => Math.max(1, p - 1))}
              disabled={reviewPage === 1}
              className="px-4 py-2 border border-gray-300 rounded-lg text-sm disabled:opacity-40 hover:bg-gray-50"
            >
              Previous
            </button>
            <span className="px-4 py-2 text-sm text-gray-600">
              Page {reviewPage} of {reviewData?.reviews.pages}
            </span>
            <button
              onClick={() => setReviewPage((p) => p + 1)}
              disabled={reviewPage === reviewData?.reviews.pages}
              className="px-4 py-2 border border-gray-300 rounded-lg text-sm disabled:opacity-40 hover:bg-gray-50"
            >
              Next
            </button>
          </div>
        )}
      </section>
    </div>
  )
}
