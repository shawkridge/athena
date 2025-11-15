/**
 * Component for displaying agent progress and metrics
 */

import { AgentProgress } from "@/types/streaming";

interface AgentProgressComponentProps {
  agents: Record<string, AgentProgress>;
  totalFindings: number;
}

const getStatusColor = (status: string): string => {
  switch (status) {
    case "running":
      return "text-blue-400";
    case "complete":
      return "text-green-400";
    case "waiting":
      return "text-yellow-400";
    default:
      return "text-gray-400";
  }
};

const getStatusBgColor = (status: string): string => {
  switch (status) {
    case "running":
      return "bg-blue-900/30";
    case "complete":
      return "bg-green-900/30";
    case "waiting":
      return "bg-yellow-900/30";
    default:
      return "bg-gray-900/30";
  }
};

const getStatusIndicatorColor = (status: string): string => {
  switch (status) {
    case "running":
      return "bg-blue-500 animate-pulse";
    case "complete":
      return "bg-green-500";
    case "waiting":
      return "bg-yellow-500";
    default:
      return "bg-gray-500";
  }
};

export const AgentProgressComponent = ({
  agents,
  totalFindings,
}: AgentProgressComponentProps) => {
  const agentList = Object.values(agents);

  if (agentList.length === 0) {
    return (
      <div className="rounded-lg border border-gray-700 bg-gray-800 p-6">
        <h3 className="mb-4 text-xl font-bold text-gray-50">Agent Progress</h3>
        <div className="flex h-32 items-center justify-center">
          <p className="text-gray-400">No agents active</p>
        </div>
      </div>
    );
  }

  // Calculate overall metrics
  const totalFindingsCounted = agentList.reduce(
    (sum, agent) => sum + agent.findings_count,
    0
  );
  const avgRate =
    agentList.length > 0
      ? agentList.reduce((sum, agent) => sum + agent.rate, 0) / agentList.length
      : 0;
  const minEta = Math.min(
    ...agentList
      .filter((a) => a.eta_seconds !== undefined)
      .map((a) => a.eta_seconds ?? Infinity)
  );

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-800 p-6">
      {/* Header with overall metrics */}
      <div className="mb-6">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-xl font-bold text-gray-50">Agent Progress</h3>
          <div className="flex gap-4 text-sm">
            <div className="text-center">
              <p className="text-gray-400">Findings/sec</p>
              <p className="text-lg font-semibold text-blue-400">
                {avgRate.toFixed(1)}
              </p>
            </div>
            {minEta !== Infinity && (
              <div className="text-center">
                <p className="text-gray-400">ETA</p>
                <p className="text-lg font-semibold text-green-400">
                  {minEta < 60 ? `${minEta.toFixed(0)}s` : `${(minEta / 60).toFixed(1)}m`}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Overall progress bar */}
        {totalFindings > 0 && (
          <div>
            <div className="mb-2 flex justify-between text-xs text-gray-400">
              <span>Overall Progress</span>
              <span>
                {totalFindingsCounted} / {totalFindings}
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-gray-700">
              <div
                className="h-full bg-gradient-to-r from-green-500 to-emerald-500 transition-all duration-300"
                style={{
                  width: `${(totalFindingsCounted / totalFindings) * 100}%`,
                }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Agent list */}
      <div className="space-y-4">
        {agentList.map((agent) => (
          <div
            key={agent.agent_id}
            className={`rounded-lg border border-gray-700 p-4 ${getStatusBgColor(agent.status)}`}
          >
            {/* Agent header */}
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`h-2 w-2 rounded-full ${getStatusIndicatorColor(agent.status)}`} />
                <div>
                  <p className="font-semibold text-gray-50">{agent.name}</p>
                  <p className={`text-xs ${getStatusColor(agent.status)}`}>
                    {agent.status.toUpperCase()}
                  </p>
                </div>
              </div>
              <div className="text-right text-sm">
                {agent.latency_ms !== undefined && (
                  <p className="text-gray-400">
                    {agent.latency_ms.toFixed(0)}ms latency
                  </p>
                )}
              </div>
            </div>

            {/* Progress bar */}
            {agent.total_findings > 0 && (
              <div className="mb-3">
                <div className="mb-1 flex justify-between text-xs text-gray-400">
                  <span>Progress</span>
                  <span>
                    {agent.findings_count} / {agent.total_findings}
                  </span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-gray-700">
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all duration-300"
                    style={{
                      width: `${(agent.findings_count / agent.total_findings) * 100}%`,
                    }}
                  />
                </div>
              </div>
            )}

            {/* Metrics */}
            <div className="grid grid-cols-3 gap-2 text-xs text-gray-400">
              <div>
                <p className="text-gray-500">Rate</p>
                <p className="font-semibold text-gray-300">
                  {agent.rate.toFixed(2)} /s
                </p>
              </div>
              {agent.eta_seconds !== undefined && (
                <div>
                  <p className="text-gray-500">ETA</p>
                  <p className="font-semibold text-gray-300">
                    {agent.eta_seconds < 60
                      ? `${agent.eta_seconds.toFixed(0)}s`
                      : `${(agent.eta_seconds / 60).toFixed(1)}m`}
                  </p>
                </div>
              )}
              <div>
                <p className="text-gray-500">Status</p>
                <p className="font-semibold text-gray-300">
                  {agent.status === "complete" ? "✓" : "→"}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AgentProgressComponent;
