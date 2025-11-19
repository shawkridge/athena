'use client'

import { Star } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useFavorites } from '@/providers/favorites-provider'
import { useToast } from '@/providers/toast-provider'

interface FavoriteStarProps {
  id: string
  title: string
  path: string
  className?: string
  size?: number
  showLabel?: boolean
}

export function FavoriteStar({
  id,
  title,
  path,
  className,
  size = 20,
  showLabel = false,
}: FavoriteStarProps) {
  const { isFavorite, toggleFavorite } = useFavorites()
  const { success, info } = useToast()
  const favorited = isFavorite(id)

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()

    toggleFavorite(id, title, path)

    if (favorited) {
      info('Removed from favorites', 2000)
    } else {
      success('Added to favorites', 2000)
    }
  }

  return (
    <button
      onClick={handleClick}
      className={cn(
        'inline-flex items-center gap-1.5 p-1.5 rounded-md transition-all',
        'hover:bg-muted active:scale-95',
        'focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2',
        className
      )}
      aria-label={favorited ? 'Remove from favorites' : 'Add to favorites'}
      title={favorited ? 'Remove from favorites' : 'Add to favorites'}
    >
      <Star
        className={cn(
          'transition-colors',
          favorited
            ? 'fill-yellow-400 text-yellow-400'
            : 'text-muted-foreground hover:text-yellow-400'
        )}
        size={size}
      />
      {showLabel && (
        <span className="text-xs font-medium text-muted-foreground">
          {favorited ? 'Favorited' : 'Favorite'}
        </span>
      )}
    </button>
  )
}
