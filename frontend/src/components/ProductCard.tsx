import { Link } from 'react-router-dom'
import type { ProductListItem } from '../types'
import RatingStars from './RatingStars'
import PriceDisplay from './PriceDisplay'

interface ProductCardProps {
  product: ProductListItem;
}

export default function ProductCard({ product }: ProductCardProps) {
  return (
    <Link
      to={`/products/${product.slug}`}
      className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-md transition-shadow flex flex-col"
    >
      <div className="aspect-square bg-gray-100 flex items-center justify-center overflow-hidden">
        {product.images?.[0] ? (
          <img
            src={product.images[0]}
            alt={product.title}
            className="w-full h-full object-cover"
          />
        ) : (
          <span className="text-gray-400 text-4xl select-none">🛍️</span>
        )}
      </div>
      <div className="p-4 flex flex-col flex-1">
        <h3 className="font-medium text-gray-900 truncate">{product.title}</h3>
        {product.review_count > 0 && (
          <div className="flex items-center gap-1 mt-1">
            <RatingStars rating={product.average_rating} size={12} />
            <span className="text-xs text-gray-500">({product.review_count})</span>
          </div>
        )}
        <div className="mt-auto pt-3 flex items-center justify-between">
          <PriceDisplay amount={product.price} size="lg" />
          {product.stock === 0 && (
            <span className="text-xs text-red-500 bg-red-50 px-2 py-1 rounded">Out of stock</span>
          )}
        </div>
      </div>
    </Link>
  )
}
