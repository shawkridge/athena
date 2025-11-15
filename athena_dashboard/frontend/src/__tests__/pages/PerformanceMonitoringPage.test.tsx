import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { PerformanceMonitoringPage } from '@/pages/PerformanceMonitoringPage'
import { ProjectProvider } from '@/context/ProjectContext'
import * as useRealtimeDataModule from '@/hooks'

// Mock data
const mockPerformanceData = {
  current: {
    cpuUsage: 48.5,
    memoryUsage: 62.3,
    memoryAvailable: 14336,
    queryLatency: 95.2,
    apiResponseTime: 185.7,
    activeConnections: 4,
    diskUsage: 68.5,
  },
  trends: [
    {
      timestamp: '2025-11-15T00:00:00Z',
      cpuUsage: 45,
      memoryUsage: 55,
      queryLatency: 80,
      apiResponseTime: 150,
    },
    {
      timestamp: '2025-11-15T06:00:00Z',
      cpuUsage: 52,
      memoryUsage: 62,
      queryLatency: 95,
      apiResponseTime: 185,
    },
  ],
  topQueries: [
    { name: 'search_episodic_events', avgLatency: 125.5, count: 342 },
    { name: 'compute_consolidation_metrics', avgLatency: 98.3, count: 156 },
  ],
  alerts: [
    {
      id: 'alert1',
      level: 'warning',
      message: 'CPU usage exceeding 80%',
      timestamp: '2025-11-15T12:00:00Z',
    },
  ],
  health: {
    status: 'healthy',
    score: 0.85,
    components: {
      cpu: 'ok',
      memory: 'ok',
      database: 'ok',
      api: 'ok',
    },
  },
}

describe('PerformanceMonitoringPage', () => {
  beforeEach(() => {
    jest.spyOn(useRealtimeDataModule, 'useRealtimeData').mockReturnValue({
      data: mockPerformanceData,
      loading: false,
      error: null,
      refetch: jest.fn(),
      isConnected: true,
    } as any)
  })

  afterEach(() => {
    jest.restoreAllMocks()
  })

  test('renders performance monitoring page with title', () => {
    render(
      <ProjectProvider>
        <PerformanceMonitoringPage />
      </ProjectProvider>
    )

    expect(screen.getByText('Performance Monitoring')).toBeInTheDocument()
  })

  test('displays system health status', () => {
    render(
      <ProjectProvider>
        <PerformanceMonitoringPage />
      </ProjectProvider>
    )

    expect(screen.getByText('System Health')).toBeInTheDocument()
    expect(screen.getByText('healthy')).toBeInTheDocument()
  })

  test('shows current metrics', () => {
    render(
      <ProjectProvider>
        <PerformanceMonitoringPage />
      </ProjectProvider>
    )

    expect(screen.getByText('CPU Usage')).toBeInTheDocument()
    expect(screen.getByText('Memory Usage')).toBeInTheDocument()
    expect(screen.getByText('Query Latency')).toBeInTheDocument()
    expect(screen.getByText('API Response')).toBeInTheDocument()
  })

  test('displays top slow queries', () => {
    render(
      <ProjectProvider>
        <PerformanceMonitoringPage />
      </ProjectProvider>
    )

    expect(screen.getByText('Top Slow Queries')).toBeInTheDocument()
    expect(screen.getByText('search_episodic_events')).toBeInTheDocument()
  })

  test('displays performance alerts', () => {
    render(
      <ProjectProvider>
        <PerformanceMonitoringPage />
      </ProjectProvider>
    )

    expect(screen.getByText('Active Alerts')).toBeInTheDocument()
    expect(screen.getByText('CPU usage exceeding 80%')).toBeInTheDocument()
  })

  test('renders time range selector', () => {
    render(
      <ProjectProvider>
        <PerformanceMonitoringPage />
      </ProjectProvider>
    )

    expect(screen.getByText('1h')).toBeInTheDocument()
    expect(screen.getByText('6h')).toBeInTheDocument()
    expect(screen.getByText('24h')).toBeInTheDocument()
  })

  test('allows changing time range', async () => {
    const user = userEvent.setup()
    render(
      <ProjectProvider>
        <PerformanceMonitoringPage />
      </ProjectProvider>
    )

    const btn24h = screen.getByText('24h').closest('button')!
    await user.click(btn24h)

    expect(btn24h).toHaveClass('bg-blue-600')
  })

  test('shows loading state', () => {
    jest.spyOn(useRealtimeDataModule, 'useRealtimeData').mockReturnValue({
      data: null,
      loading: true,
      error: null,
      refetch: jest.fn(),
      isConnected: true,
    } as any)

    render(
      <ProjectProvider>
        <PerformanceMonitoringPage />
      </ProjectProvider>
    )

    expect(screen.getByText('Performance Monitoring')).toBeInTheDocument()
    const elements = screen.getAllByTestId((content, element) => {
      return element?.className?.includes('animate-pulse') ?? false
    })
    expect(elements.length).toBeGreaterThan(0)
  })

  test('shows error state', () => {
    jest.spyOn(useRealtimeDataModule, 'useRealtimeData').mockReturnValue({
      data: null,
      loading: false,
      error: new Error('Failed to load metrics'),
      refetch: jest.fn(),
      isConnected: false,
    } as any)

    render(
      <ProjectProvider>
        <PerformanceMonitoringPage />
      </ProjectProvider>
    )

    expect(screen.getByText('Failed to load performance metrics')).toBeInTheDocument()
  })
})
