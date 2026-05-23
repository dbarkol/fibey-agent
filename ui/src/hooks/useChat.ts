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
          // Update existing activity for same tool if status changed
          const existing = prev.findIndex(
            (a) => a.tool === event.tool && a.status !== "complete"
          );
          if (existing >= 0 && event.status !== "running") {
            const updated = [...prev];
            updated[existing] = activity;
            return updated;
          }
          return [...prev, activity];
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

  return {
    messages,
    activities,
    isStreaming,
    send,
    resetChat,
  };
}
