import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Trash2, Star } from 'lucide-react'
import { useAdminReviews, useAdminDeleteReview } from '../../hooks/useAdmin'
import LoadingSpinner from '../../components/LoadingSpinner'
import Pagination from '../../components/Pagination'
import { useToast } from '../../components/Toast'

function StarRating({ rating }: { rating: number }) {
  return (
    <span className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((s) => (
        <Star
          key={s}
          size={13}
          className={s <= rating ? 'fill-amber-400 text-amber-400' : 'text-gray-200'}
        />
      ))}
    </span>
  )
}

export default function AdminReviewsPage() {
  const [page, setPage] = useState(1)
  const [minRating, setMinRating] = useState<number | undefined>()
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)

  const { data, isLoading } = useAdminReviews(page, 20, minRating)
  const { mutate: deleteReview, isPending: isDeleting } = useAdminDeleteReview()
  const toast = useToast()

  const handleDelete = (id: string) => {
    deleteReview(id, {
      onSuccess: () => {
        toast('Review deleted', 'success')
        setConfirmDelete(null)
      },
      onError: () => {
        toast('Failed to delete review', 'error')
        setConfirmDelete(null)
      },
    })
  }

  if (isLoading) return <LoadingSpinner className="py-20" size="lg" />

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Reviews</h1>
        <span className="text-sm text-gray-500">{data?.total ?? 0} total</span>
      </div>

      <div className="flex gap-3 mb-6">
        <select
          value={minRating ?? ''}
          onChange={(e) => { setMinRating(e.target.value ? Number(e.target.value) : undefined); setPage(1) }}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
        >
          <option value="">All ratings</option>
          <option value="5">5 stars only</option>
          <option value="4">4+ stars</option>
          <option value="3">3+ stars</option>
          <option value="2">2+ stars</option>
          <option value="1">1+ star</option>
        </select>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Product</th>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Reviewer</th>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Rating</th>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Review</th>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Date</th>
              <th className="text-right px-4 py-3 text-gray-600 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data?.items.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-gray-400">No reviews found</td>
              </tr>
            )}
            {data?.items.map((review) => (
              <tr key={review.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  {review.product ? (
                    <Link
                      to={`/products/${review.product.slug}`}
                      className="font-medium text-indigo-600 hover:underline line-clamp-1 max-w-[160px] block"
                    >
                      {review.product.title}
                    </Link>
                  ) : (
                    <span className="text-gray-400 italic">deleted</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-full bg-indigo-100 text-indigo-700 font-semibold text-xs flex items-center justify-center shrink-0">
                      {(review.user.full_name ?? 'U').slice(0, 2).toUpperCase()}
                    </div>
                    <span className="text-gray-700">{review.user.full_name ?? '—'}</span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <StarRating rating={review.rating} />
                </td>
                <td className="px-4 py-3 max-w-xs">
                  {review.title && <p className="font-medium text-gray-900 truncate">{review.title}</p>}
                  {review.body && <p className="text-gray-500 text-xs line-clamp-2">{review.body}</p>}
                  {review.is_verified_purchase && (
                    <span className="mt-0.5 inline-block text-xs text-green-600 font-medium">Verified</span>
                  )}
                </td>
                <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                  {new Date(review.created_at).toLocaleDateString('en-IN')}
                </td>
                <td className="px-4 py-3 text-right">
                  {confirmDelete === review.id ? (
                    <div className="flex items-center justify-end gap-2">
                      <span className="text-xs text-gray-500">Delete?</span>
                      <button
                        onClick={() => handleDelete(review.id)}
                        disabled={isDeleting}
                        className="text-xs font-medium text-red-600 hover:text-red-700 px-2 py-1 rounded hover:bg-red-50"
                      >
                        Yes
                      </button>
                      <button
                        onClick={() => setConfirmDelete(null)}
                        className="text-xs font-medium text-gray-500 hover:text-gray-700 px-2 py-1 rounded hover:bg-gray-100"
                      >
                        No
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setConfirmDelete(review.id)}
                      className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                      title="Delete review"
                    >
                      <Trash2 size={15} />
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data && <Pagination page={page} pages={data.pages} total={data.total} onPageChange={setPage} />}
    </div>
  )
}
