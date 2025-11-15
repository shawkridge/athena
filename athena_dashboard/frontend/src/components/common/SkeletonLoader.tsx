/**
 * Skeleton loader for animated placeholder while loading
 */

interface SkeletonLoaderProps {
  count?: number
  height?: string
  width?: string
  circle?: boolean
  className?: string
}

export const SkeletonLoader = ({
  count = 1,
  height = 'h-4',
  width = 'w-full',
  circle = false,
  className = '',
}: SkeletonLoaderProps) => {
  return (
    <div className={className}>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className={`${height} ${width} ${
            circle ? 'rounded-full' : 'rounded'
          } bg-gray-700 animate-pulse mb-3`}
        />
      ))}
    </div>
  )
}

export default SkeletonLoader

/**
 * Skeleton for a card layout
 */
export const CardSkeleton = () => {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 space-y-4">
      <SkeletonLoader height="h-6" width="w-1/3" />
      <SkeletonLoader count={3} height="h-4" width="w-full" />
      <div className="pt-2">
        <SkeletonLoader count={2} height="h-3" width="w-full" />
      </div>
    </div>
  )
}

/**
 * Skeleton for a table row
 */
export const TableRowSkeleton = () => {
  return (
    <tr className="border-b border-gray-700/50">
      <td className="py-3 px-3">
        <SkeletonLoader height="h-4" width="w-32" />
      </td>
      <td className="py-3 px-3">
        <SkeletonLoader height="h-4" width="w-24" />
      </td>
      <td className="py-3 px-3">
        <SkeletonLoader height="h-4" width="w-20" />
      </td>
      <td className="py-3 px-3">
        <SkeletonLoader height="h-4" width="w-28" />
      </td>
    </tr>
  )
}
