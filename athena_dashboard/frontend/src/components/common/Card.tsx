import { ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  header?: ReactNode
  footer?: ReactNode
  actions?: ReactNode
  className?: string
}

/**
 * Reusable Card component for content containers
 */
export const Card = ({
  children,
  header,
  footer,
  actions,
  className = '',
}: CardProps) => {
  return (
    <div className={`bg-gray-800 border border-gray-700 rounded-lg ${className}`}>
      {header && (
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <div>{header}</div>
          {actions && <div className="flex gap-2">{actions}</div>}
        </div>
      )}
      <div className="p-6">{children}</div>
      {footer && (
        <div className="p-4 border-t border-gray-700 bg-gray-900/50">{footer}</div>
      )}
    </div>
  )
}

export default Card
