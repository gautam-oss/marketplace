import { Star } from 'lucide-react'

interface RatingStarsProps {
  rating: number;
  max?: number;
  size?: number;
  showValue?: boolean;
  interactive?: boolean;
  onChange?: (rating: number) => void;
}

export default function RatingStars({
  rating,
  max = 5,
  size = 16,
  showValue = false,
  interactive = false,
  onChange,
}: RatingStarsProps) {
  return (
    <div className="flex items-center gap-1">
      {Array.from({ length: max }, (_, i) => {
        const filled = i < Math.round(rating)
        return (
          <Star
            key={i}
            size={size}
            className={`${filled ? 'text-amber-400 fill-amber-400' : 'text-gray-300'} ${
              interactive ? 'cursor-pointer hover:text-amber-400 hover:fill-amber-400' : ''
            } transition-colors`}
            onClick={interactive && onChange ? () => onChange(i + 1) : undefined}
          />
        )
      })}
      {showValue && (
        <span className="text-sm text-gray-600 ml-1">{rating.toFixed(1)}</span>
      )}
    </div>
  )
}
