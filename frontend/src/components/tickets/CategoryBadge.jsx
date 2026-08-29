import { Tag } from 'lucide-react'
import { categoryColor } from './constants'

export default function CategoryBadge({ category, size = 'sm' }) {
  const sizes = {
    sm: 'px-2.5 py-1 text-[11px]',
    md: 'px-3 py-1.5 text-xs',
    lg: 'px-4 py-2 text-sm'
  }

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full font-semibold border ${categoryColor(category)} ${sizes[size]}`}>
      <Tag className={size === 'sm' ? 'w-3 h-3' : 'w-4 h-4'} />
      {category}
    </span>
  )
}
