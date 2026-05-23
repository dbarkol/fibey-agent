import type { ActivityEvent } from "../api/client";

interface ActivitySidebarProps {
  activities: ActivityEvent[];
  isStreaming: boolean;
}

function statusIcon(status: ActivityEvent["status"]): string {
  switch (status) {
    case "pending":
      return "⏳";
    case "running":
      return "⚡";
    case "complete":
      return "✅";
    case "error":
      return "❌";
  }
}

function statusColor(status: ActivityEvent["status"]): string {
  switch (status) {
    case "pending":
      return "text-yellow-600 dark:text-yellow-400";
    case "running":
      return "text-blue-600 dark:text-blue-400";
    case "complete":
      return "text-green-600 dark:text-green-400";
    case "error":
      return "text-red-600 dark:text-red-400";
  }
}

export default function ActivitySidebar({ activities, isStreaming }: ActivitySidebarProps) {
  const toolCalls = activities.filter((a) => a.status === "complete").length;
  const activeTools = activities.filter((a) => a.status === "running").length;

  return (
    <div className="flex w-80 flex-col border-l border-gray-200 bg-gray-50 dark:border-gray-800 dark:bg-gray-900">
      {/* Header */}
      <div className="border-b border-gray-200 px-4 py-3 dark:border-gray-800">
        <h2 className="text-sm font-semibold">Activity</h2>
        {isStreaming && (
          <p className="mt-0.5 text-xs text-blue-600 dark:text-blue-400">
            Agent working…
          </p>
        )}
      </div>

      {/* Events */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        {activities.length === 0 ? (
          <p className="text-center text-xs text-gray-400 dark:text-gray-600">
            Tool activity will appear here as the agent works.
          </p>
        ) : (
          <div className="space-y-2">
            {activities.map((activity) => (
              <div
                key={activity.id}
                className="rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800"
              >
                <div className="flex items-center gap-2">
                  <span>{statusIcon(activity.status)}</span>
                  <span className="text-sm font-medium">{activity.tool}</span>
                  <span className={`ml-auto text-xs ${statusColor(activity.status)}`}>
                    {activity.status}
                  </span>
                </div>
                {activity.detail && (
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    {activity.detail}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer stats */}
      <div className="border-t border-gray-200 px-4 py-2 dark:border-gray-800">
        <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
          <span>{toolCalls} completed</span>
          <span>{activeTools} active</span>
          <span>{activities.length} total</span>
        </div>
      </div>
    </div>
  );
}
