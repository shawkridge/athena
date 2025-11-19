import { Download } from 'lucide-react'
import { useState } from 'react'

interface ExportButtonProps {
  data: any[]
  filename: string
  className?: string
}

export function ExportButton({ data, filename, className = '' }: ExportButtonProps) {
  const [isOpen, setIsOpen] = useState(false)

  const exportToCSV = () => {
    if (!data || data.length === 0) return

    // Get headers from first object
    const headers = Object.keys(data[0])
    const csvHeaders = headers.join(',')

    // Convert data to CSV rows
    const csvRows = data.map((row) =>
      headers.map((header) => {
        const value = row[header]
        // Escape quotes and wrap in quotes if contains comma
        const stringValue = String(value ?? '')
        return stringValue.includes(',') || stringValue.includes('"')
          ? `"${stringValue.replace(/"/g, '""')}"`
          : stringValue
      }).join(',')
    )

    const csv = [csvHeaders, ...csvRows].join('\n')
    downloadFile(csv, `${filename}.csv`, 'text/csv')
    setIsOpen(false)
  }

  const exportToJSON = () => {
    if (!data || data.length === 0) return

    const json = JSON.stringify(data, null, 2)
    downloadFile(json, `${filename}.json`, 'application/json')
    setIsOpen(false)
  }

  const downloadFile = (content: string, filename: string, mimeType: string) => {
    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const hasData = data && data.length > 0

  return (
    <div className={`relative ${className}`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={!hasData}
        className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        title={hasData ? 'Export data' : 'No data to export'}
      >
        <Download className="h-4 w-4" />
        <span className="text-sm">Export</span>
      </button>

      {isOpen && hasData && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute top-full right-0 mt-1 w-40 bg-white border rounded-md shadow-lg z-20">
            <div className="py-1">
              <button
                onClick={exportToCSV}
                className="w-full px-4 py-2 text-left text-sm hover:bg-accent transition-colors"
              >
                Export as CSV
              </button>
              <button
                onClick={exportToJSON}
                className="w-full px-4 py-2 text-left text-sm hover:bg-accent transition-colors"
              >
                Export as JSON
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
