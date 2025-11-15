import { ReactNode } from 'react'

type BadgeVariant = 'default' | 'success' | 'warning' | 'error' | 'info'

interface BadgeProps {
  children: ReactNode
  variant?: BadgeVariant
  className?: string
}

const variantStyles: Record<BadgeVariant, string> = {
  default: 'bg-gray-700 text-gray-200',
  success: 'bg-green-900/30 text-green-300',
  warning: 'bg-yellow-900/30 text-yellow-300',
  error: 'bg-red-900/30 text-red-300',
  info: 'bg-blue-900/30 text-blue-300',
}

/**
 * Badge component for labels and tags
 */
export const Badge = ({
  children,
  variant = 'default',
  className = '',
}: BadgeProps) => {
  return (
    <span
      className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-medium ${
        variantStyles[variant]
      } ${className}`}
    >
      {children}
    </span>
  )
}

export default Badge
