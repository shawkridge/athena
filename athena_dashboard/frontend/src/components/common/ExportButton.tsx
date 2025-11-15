/**
 * Export button component with format selection and export handling
 */

import { useState } from 'react'
import { ExportFormat } from '@/utils/exportData'
import { useDataExport, type ExportOptions } from '@/hooks/useDataExport'

interface ExportButtonProps<T> {
  data: T[]
  defaultFilename: string
  formats?: ExportFormat[]
  onExport?: (format: ExportFormat, size: number) => void
  onError?: (error: Error) => void
  disabled?: boolean
  className?: string
}

const DEFAULT_FORMATS: ExportFormat[] = ['json', 'csv', 'sql']

export const ExportButton = <T extends Record<string, any> = any>({
  data,
  defaultFilename,
  formats = DEFAULT_FORMATS,
  onExport,
  onError,
  disabled = false,
  className = '',
}: ExportButtonProps<T>) => {
  const [showMenu, setShowMenu] = useState(false)
  const { exporting, export: exportData, formatSize } = useDataExport<T>()

  const handleExport = async (format: ExportFormat) => {
    try {
      const result = await exportData(data, {
        format,
        filename: `${defaultFilename}-${new Date().toISOString().slice(0, 10)}`,
      })

      onExport?.(format, result.size)
      setShowMenu(false)
    } catch (error) {
      const err = error instanceof Error ? error : new Error(String(error))
      onError?.(err)
    }
  }

  const formatNames: Record<ExportFormat, string> = {
    json: 'JSON',
    csv: 'CSV (Excel)',
    sql: 'SQL Dump',
  }

  return (
    <div className={`relative ${className}`}>
      {/* Main button */}
      <button
        onClick={() => setShowMenu(!showMenu)}
        disabled={disabled || data.length === 0 || exporting}
        className={`
          inline-flex items-center gap-2 px-4 py-2 rounded-lg font-medium
          transition-colors duration-200
          ${
            disabled || data.length === 0 || exporting
              ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
              : 'bg-green-600 hover:bg-green-700 text-white cursor-pointer'
          }
        `}
        title={data.length === 0 ? 'No data to export' : 'Export data to file'}
      >
        <svg
          className={`w-4 h-4 ${exporting ? 'animate-spin' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 19l9 2-9-18-9 18 9-2m0 0v-8m0 8l-6-4m6 4l6-4"
          />
        </svg>
        {exporting ? 'Exporting...' : 'Export'}
      </button>

      {/* Dropdown menu */}
      {showMenu && (
        <div className="absolute right-0 mt-2 w-48 bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-50">
          <div className="py-1">
            {formats.map((format) => (
              <button
                key={format}
                onClick={() => handleExport(format)}
                disabled={exporting}
                className={`
                  w-full text-left px-4 py-2 text-sm
                  ${
                    exporting
                      ? 'text-gray-600 cursor-not-allowed'
                      : 'text-gray-50 hover:bg-gray-700 cursor-pointer'
                  }
                `}
              >
                <div className="font-medium">{formatNames[format]}</div>
                <div className="text-xs text-gray-500">
                  {data.length} records
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Close menu on escape */}
      {showMenu && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setShowMenu(false)}
        />
      )}
    </div>
  )
}

/**
 * Export stats component showing what will be exported
 */
export const ExportStats = <T extends Record<string, any> = any>({
  data,
  formats = DEFAULT_FORMATS,
}: {
  data: T[]
  formats?: ExportFormat[]
}) => {
  const { getExportSize, formatSize } = useDataExport<T>()

  return (
    <div className="flex gap-4 text-sm text-gray-400">
      <div>
        <span className="text-gray-50 font-semibold">{data.length}</span> records
      </div>
      {formats.map((format) => {
        const size = getExportSize(data, format)
        return (
          <div key={format}>
            <span className="text-gray-50 font-semibold">{formatSize(size)}</span>{' '}
            as {format.toUpperCase()}
          </div>
        )
      })}
    </div>
  )
}
