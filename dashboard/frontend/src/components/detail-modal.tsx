import { X } from 'lucide-react'
import { ReactNode } from 'react'

interface DetailModalProps {
  isOpen: boolean
  onClose: () => void
  title: string
  children: ReactNode
}

export function DetailModal({ isOpen, onClose, title, children }: DetailModalProps) {
  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40 animate-in fade-in"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden animate-in zoom-in-95">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b">
            <h2 className="text-xl font-semibold">{title}</h2>
            <button
              onClick={onClose}
              className="p-2 hover:bg-accent rounded-md transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Content */}
          <div className="p-6 overflow-y-auto max-h-[calc(90vh-80px)]">
            {children}
          </div>
        </div>
      </div>
    </>
  )
}

interface DetailFieldProps {
  label: string
  value: string | number | ReactNode
  className?: string
}

export function DetailField({ label, value, className = '' }: DetailFieldProps) {
  return (
    <div className={`space-y-1 ${className}`}>
      <div className="text-sm font-medium text-muted-foreground">{label}</div>
      <div className="text-sm">{value || '-'}</div>
    </div>
  )
}
