/**
 * Component for displaying research findings in real-time
 */

import { useState, useEffect, useRef } from "react";
import { Finding, EventType, StreamingUpdate } from "@/types/streaming";

interface StreamingResearchProps {
  findings: Finding[];
  totalFindings: number;
  isActive: boolean;
  onUpdate?: (update: StreamingUpdate) => void;
}

export const StreamingResearch = ({
  findings,
  totalFindings,
  isActive,
}: StreamingResearchProps) => {
  const [displayedFindings, setDisplayedFindings] = useState<Finding[]>([]);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Animate new findings
  useEffect(() => {
    setDisplayedFindings(findings);

    // Auto-scroll to bottom when new findings arrive
    if (scrollContainerRef.current) {
      setTimeout(() => {
        scrollContainerRef.current?.scrollTo({
          top: scrollContainerRef.current.scrollHeight,
          behavior: "smooth",
        });
      }, 100);
    }
  }, [findings]);

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-800 p-6">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-xl font-bold text-gray-50">Research Findings</h3>
        <div className="flex items-center gap-2">
          {isActive && (
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 animate-pulse rounded-full bg-green-500" />
              <span className="text-sm text-green-400">Streaming</span>
            </div>
          )}
          <span className="rounded-full bg-gray-700 px-3 py-1 text-sm font-medium">
            {displayedFindings.length} / {totalFindings}
          </span>
        </div>
      </div>

      {/* Progress bar */}
      {totalFindings > 0 && (
        <div className="mb-4 h-2 overflow-hidden rounded-full bg-gray-700">
          <div
            className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all duration-300"
            style={{
              width: `${(displayedFindings.length / totalFindings) * 100}%`,
            }}
          />
        </div>
      )}

      {/* Findings list */}
      <div
        ref={scrollContainerRef}
        className="max-h-96 space-y-3 overflow-y-auto"
      >
        {displayedFindings.length === 0 ? (
          <div className="flex h-40 items-center justify-center">
            <div className="text-center">
              <p className="text-gray-400">
                {isActive
                  ? "Waiting for findings..."
                  : "No findings yet"}
              </p>
            </div>
          </div>
        ) : (
          displayedFindings.map((finding, index) => (
            <div
              key={finding.id || index}
              className="animate-slide-in rounded-lg border border-gray-700 bg-gray-700/50 p-4 transition-all hover:border-gray-600 hover:bg-gray-700/75"
            >
              <div className="mb-2 flex items-start justify-between">
                <h4 className="flex-1 font-semibold text-gray-50">
                  {finding.title}
                </h4>
                <span className="ml-2 rounded-full bg-blue-900/50 px-2 py-1 text-xs text-blue-300">
                  {(finding.relevance_score * 100).toFixed(0)}%
                </span>
              </div>

              <p className="mb-2 text-sm text-gray-300 line-clamp-2">
                {finding.content}
              </p>

              <div className="flex items-center justify-between text-xs text-gray-400">
                {finding.source && (
                  <span className="truncate hover:text-gray-300">
                    📌 {finding.source}
                  </span>
                )}
                {finding.timestamp && (
                  <span className="ml-2">
                    {new Date(finding.timestamp).toLocaleTimeString()}
                  </span>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Status footer */}
      {totalFindings > 0 && displayedFindings.length < totalFindings && (
        <div className="mt-4 rounded-lg border border-gray-700 bg-gray-700/30 p-3 text-center text-sm text-gray-400">
          Loaded {displayedFindings.length} of {totalFindings} findings...
        </div>
      )}
    </div>
  );
};

export default StreamingResearch;
