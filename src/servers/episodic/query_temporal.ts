/**
 * Episodic Memory: Temporal Queries
 *
 * Query memories based on temporal (time-based) patterns
 */

import type { Memory, TemporalQueryInput } from './types';

declare const callMCPTool: (operation: string, params: unknown) => Promise<unknown>;

/**
 * Query memories within a time range
 *
 * Retrieves memories created between start and end timestamps.
 *
 * @param startTime - Start timestamp (ms since epoch)
 * @param endTime - End timestamp (ms since epoch)
 * @param limit - Maximum results
 * @param sortBy - Sort by 'timestamp' or 'confidence'
 * @returns Memories in time range
 *
 * @example
 * const today = new Date().setHours(0, 0, 0, 0);
 * const tomorrow = today + 24 * 60 * 60 * 1000;
 * const todayMemories = await queryTemporal(today, tomorrow);
 */
export async function queryTemporal(
  startTime: number,
  endTime: number,
  limit?: number,
  sortBy: 'timestamp' | 'confidence' = 'timestamp'
): Promise<Memory[]> {
  return (await callMCPTool('episodic/queryTemporal', {
    startTime,
    endTime,
    limit: limit ?? 100,
    sortBy,
  })) as Memory[];
}

/**
 * Get memories from the last N days
 *
 * Convenience method for recent memory queries.
 *
 * @param days - Number of days in the past
 * @param limit - Maximum results
 * @returns Recent memories
 *
 * @example
 * const lastWeek = await queryLastDays(7);
 * const lastMonth = await queryLastDays(30, 50);
 */
export async function queryLastDays(days: number, limit?: number): Promise<Memory[]> {
  const endTime = Date.now();
  const startTime = endTime - days * 24 * 60 * 60 * 1000;
  return await queryTemporal(startTime, endTime, limit);
}

/**
 * Get memories from a specific date
 *
 * Retrieves all memories from a given date (midnight to midnight).
 *
 * @param date - Date to query
 * @param limit - Maximum results
 * @returns Memories from that date
 *
 * @example
 * const date = new Date('2024-11-07');
 * const memories = await queryDate(date);
 */
export async function queryDate(date: Date, limit?: number): Promise<Memory[]> {
  const startTime = new Date(date).setHours(0, 0, 0, 0);
  const endTime = startTime + 24 * 60 * 60 * 1000;
  return await queryTemporal(startTime, endTime, limit);
}

/**
 * Get memories around a specific time
 *
 * Retrieves memories within a window around a timestamp.
 *
 * @param centerTime - Center timestamp
 * @param windowMs - Window size in milliseconds (±half on each side)
 * @param limit - Maximum results
 * @returns Memories in the window
 *
 * @example
 * // Get memories ±1 hour around the meeting time
 * const meetingTime = new Date('2024-11-07 14:00:00').getTime();
 * const nearby = await queryAround(meetingTime, 2 * 60 * 60 * 1000);
 */
export async function queryAround(
  centerTime: number,
  windowMs: number,
  limit?: number
): Promise<Memory[]> {
  const half = windowMs / 2;
  return await queryTemporal(centerTime - half, centerTime + half, limit);
}

/**
 * Get memories with temporal overlap
 *
 * Finds memories that overlap with a specified time period.
 *
 * @param startTime - Start of period
 * @param endTime - End of period
 * @param limit - Maximum results
 * @returns Overlapping memories
 */
export async function queryOverlap(
  startTime: number,
  endTime: number,
  limit?: number
): Promise<Memory[]> {
  return await queryTemporal(startTime, endTime, limit);
}

/**
 * Query memories grouped by time intervals
 *
 * Returns memories grouped into time buckets (hourly, daily, etc).
 *
 * @param startTime - Start timestamp
 * @param endTime - End timestamp
 * @param intervalMs - Bucket interval in milliseconds
 * @returns Memories grouped by time intervals
 *
 * @example
 * // Group memories into 1-hour buckets
 * const hourly = await queryByInterval(
 *   Date.now() - 24 * 60 * 60 * 1000,
 *   Date.now(),
 *   60 * 60 * 1000
 * );
 */
export async function queryByInterval(
  startTime: number,
  endTime: number,
  intervalMs: number
): Promise<Record<string, Memory[]>> {
  return (await callMCPTool('episodic/queryByInterval', {
    startTime,
    endTime,
    intervalMs,
  })) as Record<string, Memory[]>;
}

/**
 * Get temporal statistics
 *
 * Returns statistics about memory distribution over time.
 *
 * @param startTime - Start timestamp
 * @param endTime - End timestamp
 * @returns Statistics object
 */
export async function getTemporalStats(startTime: number, endTime: number): Promise<{
  totalMemories: number;
  averageConfidence: number;
  densestHour: number;
  memoryDensity: number; // memories per hour
}> {
  return (await callMCPTool('episodic/temporalStats', {
    startTime,
    endTime,
  })) as {
    totalMemories: number;
    averageConfidence: number;
    densestHour: number;
    memoryDensity: number;
  };
}
