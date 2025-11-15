/**
 * Hook for managing data export operations
 */

import { useState, useCallback } from 'react'
import {
  ExportFormat,
  exportToJSON,
  exportToCSV,
  exportToSQL,
  calculateExportSize,
  formatFileSize,
} from '@/utils/exportData'

export interface ExportOptions {
  format: ExportFormat
  filename: string
  tableName?: string
  includeColumns?: string[]
  filter?: (item: any) => boolean
}

export interface ExportState {
  exporting: boolean
  error: Error | null
  lastExportedAt: Date | null
  exportSize: number
}

/**
 * Hook for managing data exports
 */
export function useDataExport<T extends Record<string, any> = any>() {
  const [state, setState] = useState<ExportState>({
    exporting: false,
    error: null,
    lastExportedAt: null,
    exportSize: 0,
  })

  const export_ = useCallback(
    async (data: T[], options: ExportOptions) => {
      setState((prev) => ({ ...prev, exporting: true, error: null }))

      try {
        // Calculate size estimate
        const estimatedSize = calculateExportSize(data, options.format)

        // Apply filter if provided
        const filtered = options.filter ? data.filter(options.filter) : data

        // Perform export
        switch (options.format) {
          case 'json':
            exportToJSON(filtered, options.filename)
            break
          case 'csv':
            exportToCSV(filtered, options.filename, options.includeColumns as any)
            break
          case 'sql':
            exportToSQL(filtered, options.tableName || 'data', options.filename)
            break
        }

        setState({
          exporting: false,
          error: null,
          lastExportedAt: new Date(),
          exportSize: estimatedSize,
        })

        return {
          success: true,
          size: estimatedSize,
          filename: `${options.filename}.${options.format}`,
        }
      } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err))
        setState({
          exporting: false,
          error,
          lastExportedAt: null,
          exportSize: 0,
        })
        throw error
      }
    },
    []
  )

  const getExportSize = useCallback((data: T[], format: ExportFormat) => {
    return calculateExportSize(data, format)
  }, [])

  const formatSize = useCallback((bytes: number) => {
    return formatFileSize(bytes)
  }, [])

  return {
    ...state,
    export: export_,
    getExportSize,
    formatSize,
  }
}
