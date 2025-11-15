/**
 * Research page - main interface for real-time research monitoring
 */

import { useState, useCallback } from "react";
import StreamingResearch from "@/components/StreamingResearch";
import AgentProgress from "@/components/AgentProgress";
import MemoryHealth from "@/components/MemoryHealth";
import { useWebSocket } from "@/hooks/useWebSocket";
import { Finding, AgentProgress as AgentProgressType, EventType } from "@/types/streaming";

export const ResearchPage = () => {
  const [taskId, setTaskId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [findings, setFindings] = useState<Finding[]>([]);
  const [agents, setAgents] = useState<Record<string, AgentProgressType>>({});
  const [totalFindings, setTotalFindings] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [status, setStatus] = useState("idle");

  // WebSocket connection for streaming
  const { isConnected } = useWebSocket({
    url: taskId
      ? `ws://${window.location.hostname}:8000/ws/research/${taskId}`
      : "",
    onMessage: (update) => {
      switch (update.type) {
        case EventType.FINDING:
          if (update.data.finding) {
            setFindings((prev) => [...prev, update.data.finding]);
          }
          setTotalFindings(update.data.total_findings ?? 0);
          break;

        case EventType.PROGRESS:
          if (update.data.agent) {
            setAgents((prev) => ({
              ...prev,
              [update.data.agent.agent_id]: update.data.agent,
            }));
          }
          setTotalFindings(update.data.total_findings ?? totalFindings);
          break;

        case EventType.COMPLETE:
          setIsRunning(false);
          setStatus("completed");
          break;

        case EventType.ERROR:
          setStatus(`error: ${update.data.error}`);
          setIsRunning(false);
          break;
      }
    },
    onError: (error) => {
      console.error("WebSocket error:", error);
      setStatus(`error: ${error.message}`);
    },
    onClose: () => {
      setIsRunning(false);
    },
    autoReconnect: true,
  });

  const handleStartResearch = useCallback(async () => {
    if (!query.trim()) {
      setStatus("error: Please enter a query");
      return;
    }

    // Generate task ID
    const newTaskId = `task-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    setTaskId(newTaskId);
    setIsRunning(true);
    setStatus("starting");
    setFindings([]);
    setAgents({});
    setTotalFindings(0);

    // TODO: In a real implementation, call the research API to start the task
    // For now, we'll just set up the WebSocket connection
    console.log("Starting research task:", newTaskId, "Query:", query);
  }, [query]);

  const handleStopResearch = useCallback(() => {
    setIsRunning(false);
    setStatus("stopped");
    setTaskId(null);
  }, []);

  const handleClearResults = useCallback(() => {
    setFindings([]);
    setAgents({});
    setTotalFindings(0);
    setStatus("idle");
    setQuery("");
  }, []);

  return (
    <div className="space-y-6">
      {/* Query Input Card */}
      <div className="rounded-lg border border-gray-700 bg-gray-800 p-6">
        <h2 className="mb-4 text-2xl font-bold text-gray-50">Research Query</h2>

        <div className="space-y-4">
          {/* Query input */}
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-300">
              Research Topic
            </label>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={isRunning}
              placeholder="Enter your research topic (e.g., 'Machine learning architectures')"
              className="w-full rounded-lg border border-gray-700 bg-gray-900 px-4 py-2 text-gray-50 placeholder-gray-500 disabled:opacity-50"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !isRunning) {
                  handleStartResearch();
                }
              }}
            />
          </div>

          {/* Control buttons */}
          <div className="flex gap-3">
            <button
              onClick={handleStartResearch}
              disabled={isRunning || !query.trim()}
              className="flex-1 rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white disabled:opacity-50 hover:bg-blue-700"
            >
              {isRunning ? "Research Running..." : "Start Research"}
            </button>

            {isRunning && (
              <button
                onClick={handleStopResearch}
                className="flex-1 rounded-lg bg-red-600 px-4 py-2 font-semibold text-white hover:bg-red-700"
              >
                Stop Research
              </button>
            )}

            <button
              onClick={handleClearResults}
              disabled={findings.length === 0 && Object.keys(agents).length === 0}
              className="rounded-lg border border-gray-700 px-4 py-2 font-semibold text-gray-300 disabled:opacity-50 hover:bg-gray-700"
            >
              Clear
            </button>
          </div>

          {/* Status display */}
          <div className="rounded-lg border border-gray-700 bg-gray-700/30 p-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">
                {status === "idle" && "Ready to start research"}
                {status === "starting" && "Initializing research..."}
                {status === "completed" && "Research completed"}
                {status === "stopped" && "Research stopped"}
                {status.startsWith("error") && status}
              </span>
              {isConnected && isRunning && (
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 animate-pulse rounded-full bg-green-500" />
                  <span className="text-xs text-green-400">Connected</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Results section */}
      {(findings.length > 0 || isRunning) && (
        <>
          {/* Two-column layout */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            {/* Main results - wider */}
            <div className="lg:col-span-2">
              <StreamingResearch
                findings={findings}
                totalFindings={totalFindings}
                isActive={isRunning}
              />
            </div>

            {/* Agent progress - sidebar */}
            <div>
              <AgentProgress agents={agents} totalFindings={totalFindings} />
            </div>
          </div>

          {/* Memory health metrics */}
          <MemoryHealth
            episodicEvents={8128}
            consolidationProgress={totalFindings > 0 ? Math.min((findings.length / totalFindings) * 100, 100) : 0}
          />
        </>
      )}

      {/* Empty state */}
      {!isRunning && findings.length === 0 && (
        <div className="rounded-lg border border-dashed border-gray-700 bg-gray-800/50 p-12 text-center">
          <div className="mb-4">
            <svg className="mx-auto h-12 w-12 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <h3 className="mb-2 text-lg font-semibold text-gray-300">No research running</h3>
          <p className="mb-6 text-gray-400">Enter a query and click "Start Research" to begin</p>
          <div className="inline-block">
            <pre className="rounded-lg bg-gray-900 px-4 py-2 text-left text-sm text-gray-300">
              Example: "machine learning trends"
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};

export default ResearchPage;
