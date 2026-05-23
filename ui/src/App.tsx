import { useState } from "react";
import { useChat } from "./hooks/useChat";
import ChatPanel from "./components/ChatPanel";
import ActivitySidebar from "./components/ActivitySidebar";

export default function App() {
  const { messages, activities, isStreaming, send, resetChat } = useChat();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="flex h-screen flex-col">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-3 dark:border-gray-800 dark:bg-gray-950">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold">Fibey Field Ops</h1>
          <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900 dark:text-blue-300">
            Foundry Toolbox Demo
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={resetChat}
            className="rounded-md px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
          >
            New Chat
          </button>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="rounded-md px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
          >
            {sidebarOpen ? "Hide" : "Show"} Activity
          </button>
        </div>
      </header>

      {/* Main content */}
      <div className="flex min-h-0 flex-1">
        <ChatPanel
          messages={messages}
          isStreaming={isStreaming}
          onSend={send}
        />
        {sidebarOpen && (
          <ActivitySidebar
            activities={activities}
            isStreaming={isStreaming}
          />
        )}
      </div>
    </div>
  );
}
