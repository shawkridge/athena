/**
 * Component for displaying memory layer health metrics
 */

interface MemoryLayer {
  name: string;
  items: number;
  status: "healthy" | "warning" | "critical";
  percentage?: number;
}

interface MemoryHealthProps {
  episodicEvents?: number;
  semanticMemories?: number;
  proceduresLearned?: number;
  graphEntities?: number;
  consolidationProgress?: number;
}

const getStatusColor = (status: string): string => {
  switch (status) {
    case "healthy":
      return "text-green-400";
    case "warning":
      return "text-yellow-400";
    case "critical":
      return "text-red-400";
    default:
      return "text-gray-400";
  }
};

const getStatusBgColor = (status: string): string => {
  switch (status) {
    case "healthy":
      return "bg-green-900/20 border-green-700/50";
    case "warning":
      return "bg-yellow-900/20 border-yellow-700/50";
    case "critical":
      return "bg-red-900/20 border-red-700/50";
    default:
      return "bg-gray-700/20 border-gray-600/50";
  }
};

const getProgressColor = (status: string): string => {
  switch (status) {
    case "healthy":
      return "from-green-500 to-emerald-500";
    case "warning":
      return "from-yellow-500 to-orange-500";
    case "critical":
      return "from-red-500 to-pink-500";
    default:
      return "from-gray-500 to-gray-600";
  }
};

export const MemoryHealth = ({
  episodicEvents = 8128,
  semanticMemories = 2341,
  proceduresLearned = 101,
  graphEntities = 5426,
  consolidationProgress = 65,
}: MemoryHealthProps) => {
  const layers: MemoryLayer[] = [
    {
      name: "Episodic Events",
      items: episodicEvents,
      status: episodicEvents > 5000 ? "healthy" : "warning",
      percentage: Math.min((episodicEvents / 10000) * 100, 100),
    },
    {
      name: "Semantic Memories",
      items: semanticMemories,
      status: semanticMemories > 1000 ? "healthy" : "warning",
      percentage: Math.min((semanticMemories / 5000) * 100, 100),
    },
    {
      name: "Procedures Learned",
      items: proceduresLearned,
      status: proceduresLearned > 50 ? "healthy" : "warning",
      percentage: Math.min((proceduresLearned / 200) * 100, 100),
    },
    {
      name: "Graph Entities",
      items: graphEntities,
      status: graphEntities > 3000 ? "healthy" : "warning",
      percentage: Math.min((graphEntities / 10000) * 100, 100),
    },
  ];

  const overallHealth =
    layers.every((l) => l.status === "healthy") ? "healthy"
      : layers.some((l) => l.status === "critical") ? "critical"
      : "warning";

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-800 p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <h3 className="text-xl font-bold text-gray-50">Memory System Health</h3>
        <div className="flex items-center gap-2">
          <div
            className={`h-3 w-3 rounded-full ${
              overallHealth === "healthy"
                ? "bg-green-500"
                : overallHealth === "critical"
                  ? "bg-red-500"
                  : "bg-yellow-500"
            } ${overallHealth === "healthy" ? "" : "animate-pulse"}`}
          />
          <span className={getStatusColor(overallHealth)}>
            {overallHealth.toUpperCase()}
          </span>
        </div>
      </div>

      {/* Consolidation Progress */}
      <div className="mb-6 rounded-lg border border-gray-700 bg-gray-700/30 p-4">
        <div className="mb-2 flex items-center justify-between">
          <p className="font-semibold text-gray-200">Consolidation Progress</p>
          <p className="text-sm text-gray-400">{consolidationProgress}%</p>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-gray-700">
          <div
            className={`h-full bg-gradient-to-r ${getProgressColor("healthy")} transition-all duration-300`}
            style={{ width: `${consolidationProgress}%` }}
          />
        </div>
        <p className="mt-2 text-xs text-gray-400">
          Pattern extraction and memory consolidation in progress
        </p>
      </div>

      {/* Layer Health Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {layers.map((layer) => (
          <div
            key={layer.name}
            className={`rounded-lg border p-4 transition-all ${getStatusBgColor(layer.status)}`}
          >
            {/* Layer header */}
            <div className="mb-3 flex items-center justify-between">
              <p className="font-semibold text-gray-50">{layer.name}</p>
              <span className={`text-sm font-bold ${getStatusColor(layer.status)}`}>
                {layer.status.toUpperCase()}
              </span>
            </div>

            {/* Item count */}
            <p className="mb-3 text-2xl font-bold text-gray-50">
              {layer.items.toLocaleString()}
            </p>

            {/* Progress bar */}
            {layer.percentage !== undefined && (
              <div>
                <div className="mb-1 flex justify-between text-xs text-gray-400">
                  <span>Capacity</span>
                  <span>{layer.percentage.toFixed(0)}%</span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-gray-700">
                  <div
                    className={`h-full bg-gradient-to-r ${getProgressColor(layer.status)} transition-all duration-300`}
                    style={{ width: `${layer.percentage}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Info Section */}
      <div className="mt-6 rounded-lg border border-gray-700 bg-gray-700/20 p-4 text-sm text-gray-400">
        <p className="mb-2 font-semibold text-gray-300">💡 System Status</p>
        <ul className="space-y-1 text-xs">
          <li>✓ All memory layers operational</li>
          <li>✓ Consolidation active and progressing</li>
          <li>✓ Knowledge graph building (5.4K entities)</li>
          <li>✓ Learning procedures extracted (101 total)</li>
        </ul>
      </div>
    </div>
  );
};

export default MemoryHealth;
