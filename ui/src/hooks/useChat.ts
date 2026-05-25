import { useState, useRef, useCallback } from "react";
import {
  type ChatMessage,
  type ActivityEvent,
  sendMessage,
} from "../api/client";

let messageIdCounter = 0;
function nextMessageId(): string {
  return `msg-${++messageIdCounter}`;
}

let activityIdCounter = 0;
function nextActivityId(): string {
  return `act-${++activityIdCounter}`;
}

/** Map tool names to their parent skill */
function inferSkillFromTool(toolName: string): string | null {
  const lower = toolName.toLowerCase();
  if (lower === "knowledge_base" || lower.includes("knowledge_base")) return "knowledge-retrieval";
  if (lower.startsWith("inventory___") || lower.startsWith("inventory__")) return "inventory";
  if (lower.startsWith("work_orders___") || lower.startsWith("work_orders__")) return "work-orders";
  return null;
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [activities, setActivities] = useState<ActivityEvent[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const sessionIdRef = useRef(crypto.randomUUID());
  const assistantIdRef = useRef<string>("");

  const send = useCallback(async (text: string) => {
    if (!text.trim() || isStreaming) return;

    const userMsg: ChatMessage = {
      id: nextMessageId(),
      role: "user",
      content: text,
    };

    const assistantMsg: ChatMessage = {
      id: nextMessageId(),
      role: "assistant",
      content: "",
    };
    assistantIdRef.current = assistantMsg.id;

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setIsStreaming(true);

    // Clear previous activities for this turn
    setActivities([]);

    await sendMessage(text, sessionIdRef.current, {
      onDelta(content) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantIdRef.current
              ? { ...m, content: m.content + content }
              : m
          )
        );
      },
      onActivity(event) {
        const activity: ActivityEvent = {
          ...event,
          id: nextActivityId(),
          timestamp: Date.now(),
        };

        setActivities((prev) => {
          const updated = [...prev];

          // Synthesize a "Load Skill" entry if this is the first tool call from a skill
          if (event.status === "running") {
            const skillName = inferSkillFromTool(event.tool);
            if (skillName) {
              const alreadySeen = prev.some(
                (a) => a.tool === "load_skill" && a.detail === `Loading skill: ${skillName}`
              );
              if (!alreadySeen) {
                updated.push({
                  tool: "load_skill",
                  status: "complete",
                  detail: `Loading skill: ${skillName}`,
                  id: nextActivityId(),
                  timestamp: Date.now(),
                });
              }
            }
          }

          // Update existing activity for same call_id (or tool if no call_id)
          const matchKey = event.call_id || event.tool;
          const existing = updated.findIndex(
            (a) => (a.call_id || a.tool) === matchKey && a.status !== "complete"
          );
          if (existing >= 0) {
            // Merge: prefer newer args if present, keep existing if not
            updated[existing] = {
              ...updated[existing],
              ...activity,
              args: activity.args || updated[existing]?.args,
              result: activity.result || updated[existing]?.result,
            };
            return updated;
          }
          return [...updated, activity];
        });
      },
      onError(message) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantIdRef.current
              ? { ...m, content: m.content + `\n\n⚠️ ${message}` }
              : m
          )
        );
      },
      onDone() {
        setIsStreaming(false);
      },
    });
  }, [isStreaming]);

  const resetChat = useCallback(async () => {
    const { resetSession } = await import("../api/client");
    await resetSession(sessionIdRef.current);
    sessionIdRef.current = crypto.randomUUID();
    setMessages([]);
    setActivities([]);
  }, []);

  const clearActivities = useCallback(() => {
    setActivities([]);
  }, []);

  return {
    messages,
    activities,
    isStreaming,
    send,
    resetChat,
    clearActivities,
  };
}
