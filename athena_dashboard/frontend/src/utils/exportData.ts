/**
 * Data export utilities for JSON, CSV, and SQL formats
 */

export type ExportFormat = 'json' | 'csv' | 'sql'

/**
 * Export data to JSON format
 */
export function exportToJSON<T>(data: T[], filename: string): void {
  const jsonString = JSON.stringify(data, null, 2)
  downloadFile(jsonString, `${filename}.json`, 'application/json')
}

/**
 * Export data to CSV format
 */
export function exportToCSV<T extends Record<string, any>>(
  data: T[],
  filename: string,
  columns?: (keyof T)[]
): void {
  if (data.length === 0) {
    console.warn('No data to export')
    return
  }

  // Determine columns to include
  const selectedColumns = columns || (Object.keys(data[0]) as (keyof T)[])

  // Build CSV header
  const header = selectedColumns.map((col) => escapeCSVField(String(col))).join(',')

  // Build CSV rows
  const rows = data.map((row) =>
    selectedColumns
      .map((col) => escapeCSVField(formatCSVValue(row[col])))
      .join(',')
  )

  const csv = [header, ...rows].join('\n')
  downloadFile(csv, `${filename}.csv`, 'text/csv;charset=utf-8;')
}

/**
 * Export data to SQL format
 */
export function exportToSQL<T extends Record<string, any>>(
  data: T[],
  tableName: string,
  filename: string
): void {
  if (data.length === 0) {
    console.warn('No data to export')
    return
  }

  const columns = Object.keys(data[0])
  const statements: string[] = []

  // Add CREATE TABLE statement
  const createTable = buildCreateTableStatement(tableName, columns, data[0])
  statements.push(createTable)
  statements.push('')

  // Add INSERT statements
  data.forEach((row) => {
    const values = columns.map((col) => formatSQLValue(row[col])).join(', ')
    statements.push(`INSERT INTO ${tableName} (${columns.join(', ')}) VALUES (${values});`)
  })

  const sql = statements.join('\n')
  downloadFile(sql, `${filename}.sql`, 'text/sql;charset=utf-8;')
}

/**
 * Batch export with multiple formats
 */
export function exportMultipleFormats<T extends Record<string, any>>(
  data: T[],
  baseFilename: string,
  formats: ExportFormat[],
  tableName: string = 'data'
): void {
  formats.forEach((format) => {
    switch (format) {
      case 'json':
        exportToJSON(data, baseFilename)
        break
      case 'csv':
        exportToCSV(data, baseFilename)
        break
      case 'sql':
        exportToSQL(data, tableName, baseFilename)
        break
    }
  })
}

/**
 * Export with filtering and transformation
 */
export function exportFiltered<T extends Record<string, any>>(
  data: T[],
  format: ExportFormat,
  filename: string,
  filter?: (item: T) => boolean,
  transform?: (item: T) => Record<string, any>,
  tableName: string = 'data'
): void {
  let filtered = filter ? data.filter(filter) : data
  const transformed = transform ? filtered.map(transform) : filtered

  switch (format) {
    case 'json':
      exportToJSON(transformed, filename)
      break
    case 'csv':
      exportToCSV(transformed as any, filename)
      break
    case 'sql':
      exportToSQL(transformed as any, tableName, filename)
      break
  }
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Download file to client
 */
function downloadFile(content: string, filename: string, mimeType: string): void {
  const element = document.createElement('a')
  element.setAttribute('href', `data:${mimeType},${encodeURIComponent(content)}`)
  element.setAttribute('download', filename)
  element.style.display = 'none'

  document.body.appendChild(element)
  element.click()
  document.body.removeChild(element)
}

/**
 * Escape CSV field (handle commas, quotes, newlines)
 */
function escapeCSVField(field: string): string {
  if (field.includes(',') || field.includes('"') || field.includes('\n')) {
    return `"${field.replace(/"/g, '""')}"` // Escape quotes by doubling
  }
  return field
}

/**
 * Format value for CSV output
 */
function formatCSVValue(value: any): string {
  if (value === null || value === undefined) {
    return ''
  }
  if (typeof value === 'boolean') {
    return value ? 'true' : 'false'
  }
  if (typeof value === 'object') {
    return JSON.stringify(value)
  }
  return String(value)
}

/**
 * Format value for SQL output
 */
function formatSQLValue(value: any): string {
  if (value === null || value === undefined) {
    return 'NULL'
  }
  if (typeof value === 'string') {
    return `'${value.replace(/'/g, "''")}'` // Escape single quotes
  }
  if (typeof value === 'boolean') {
    return value ? '1' : '0'
  }
  if (typeof value === 'object') {
    return `'${JSON.stringify(value).replace(/'/g, "''")}'`
  }
  return String(value)
}

/**
 * Get SQL data type for column
 */
function getSQLDataType(value: any): string {
  if (value === null || value === undefined) {
    return 'VARCHAR(255)'
  }
  if (typeof value === 'number') {
    return Number.isInteger(value) ? 'INT' : 'DECIMAL(10,2)'
  }
  if (typeof value === 'boolean') {
    return 'BOOLEAN'
  }
  if (value instanceof Date) {
    return 'DATETIME'
  }
  if (typeof value === 'object') {
    return 'TEXT'
  }
  return `VARCHAR(${Math.max(50, String(value).length)})`
}

/**
 * Build CREATE TABLE statement
 */
function buildCreateTableStatement<T extends Record<string, any>>(
  tableName: string,
  columns: string[],
  sampleRow: T
): string {
  const columnDefinitions = columns
    .map((col) => {
      const type = getSQLDataType(sampleRow[col])
      return `  ${col} ${type}`
    })
    .join(',\n')

  return `CREATE TABLE IF NOT EXISTS ${tableName} (\n${columnDefinitions},\n  id INT PRIMARY KEY AUTO_INCREMENT\n);`
}

/**
 * Calculate data export size
 */
export function calculateExportSize<T>(data: T[], format: ExportFormat): number {
  switch (format) {
    case 'json':
      return JSON.stringify(data).length
    case 'csv':
      // Rough estimate: sum of all values + comma separators
      return JSON.stringify(data).length * 0.7
    case 'sql':
      // Rough estimate: larger due to SQL syntax
      return JSON.stringify(data).length * 1.5
    default:
      return 0
  }
}

/**
 * Format bytes to human-readable size
 */
export function formatFileSize(bytes: number): string {
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let unitIndex = 0

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }

  return `${size.toFixed(2)} ${units[unitIndex]}`
}
