interface PriceDisplayProps {
  amount: number;
  className?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

const sizeClasses = {
  sm: 'text-sm',
  md: 'text-base',
  lg: 'text-lg font-bold',
  xl: 'text-2xl font-bold',
}

export default function PriceDisplay({ amount, className = '', size = 'md' }: PriceDisplayProps) {
  const formatted = new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount)

  return (
    <span className={`text-indigo-600 ${sizeClasses[size]} ${className}`}>{formatted}</span>
  )
}
