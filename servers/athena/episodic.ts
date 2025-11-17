/**
 * Episodic Memory Operations - Event Storage & Retrieval
 *
 * These operations manage the episodic memory layer (Layer 1).
 * Episodic memory stores events with spatial-temporal grounding.
 *
 * All functions are discoverable here and map to Python implementations.
 * Agents import directly from: athena.episodic.operations
 */

export interface EpisodicEvent {
  id: string;
  content: string;
  timestamp: string;
  tags?: string[];
  source?: string;
  importance?: number;
  session_id?: string;
  context?: Record<string, any>;
}

export interface EpisodicStatistics {
  total_events: number;
  by_source: Record<string, number>;
  by_tag: Record<string, number>;
  avg_importance: number;
  time_span_days: number;
}

/**
 * Store an event in episodic memory
 *
 * Adds a new event to episodic memory with optional tags, context, and importance scoring.
 * Events are automatically given spatial-temporal grounding (session, timestamp).
 *
 * @param content - Event description or content
 * @param context - Optional context metadata
 * @param tags - Optional tags for categorization
 * @param source - Source of the event (default: "agent")
 * @param importance - Importance score 0-1 (default: 0.5)
 * @param session_id - Session identifier (default: "default")
 * @returns Event ID
 *
 * @implementation src/athena/episodic/operations.py:remember
 *
 * @example
 * ```python
 * from athena.episodic.operations import remember
 *
 * event_id = await remember(
 *   content="User asked about authentication flow",
 *   tags=["meeting", "authentication"],
 *   importance=0.8
 * )
 * print(f"Stored event: {event_id}")
 * ```
 */
export async function remember(
  content: string,
  context?: Record<string, any>,
  tags?: string[],
  source?: string,
  importance?: number,
  session_id?: string
): Promise<string>;

/**
 * Retrieve events from episodic memory
 *
 * Searches episodic memory by semantic similarity to query string.
 * Returns most relevant events ordered by relevance and importance.
 *
 * @param query - Search query (semantic)
 * @param limit - Maximum events to return (default: 10)
 * @param session_id - Filter to specific session (optional)
 * @returns List of matching events
 *
 * @implementation src/athena/episodic/operations.py:recall
 *
 * @example
 * ```python
 * from athena.episodic.operations import recall
 *
 * events = await recall("authentication implementation", limit=5)
 * for event in events:
 *   print(f"{event['timestamp']}: {event['content']}")
 * ```
 */
export async function recall(
  query: string,
  limit?: number,
  session_id?: string
): Promise<EpisodicEvent[]>;

/**
 * Retrieve recent events
 *
 * Returns most recent events across all sessions or within a specific session.
 *
 * @param limit - Number of recent events to return (default: 10)
 * @param session_id - Filter to specific session (optional)
 * @returns List of recent events
 *
 * @implementation src/athena/episodic/operations.py:recall_recent
 */
export async function recall_recent(
  limit?: number,
  session_id?: string
): Promise<EpisodicEvent[]>;

/**
 * Get events from a specific session
 *
 * @param session_id - Session identifier
 * @param limit - Maximum events to return (default: 100)
 * @returns List of events in session
 *
 * @implementation src/athena/episodic/operations.py:get_by_session
 */
export async function get_by_session(
  session_id: string,
  limit?: number
): Promise<EpisodicEvent[]>;

/**
 * Get events by tags
 *
 * Returns all events matching specified tags.
 *
 * @param tags - Tags to filter by
 * @param limit - Maximum events to return (default: 50)
 * @returns List of events with matching tags
 *
 * @implementation src/athena/episodic/operations.py:get_by_tags
 */
export async function get_by_tags(
  tags: string[],
  limit?: number
): Promise<EpisodicEvent[]>;

/**
 * Get events within a time range
 *
 * Returns events occurring between start and end timestamps.
 *
 * @param start_date - Start date (ISO format)
 * @param end_date - End date (ISO format)
 * @param limit - Maximum events to return (default: 100)
 * @returns List of events in time range
 *
 * @implementation src/athena/episodic/operations.py:get_by_time_range
 */
export async function get_by_time_range(
  start_date: string,
  end_date: string,
  limit?: number
): Promise<EpisodicEvent[]>;

/**
 * Get episodic memory statistics
 *
 * Returns aggregate statistics about episodic memory usage.
 *
 * @returns Statistics object
 *
 * @implementation src/athena/episodic/operations.py:get_statistics
 */
export async function get_statistics(): Promise<EpisodicStatistics>;
