interface Suggestion {
  prompt: string;
  tags: { label: string; color: "red" | "green" | "yellow" }[];
}

const suggestions: Suggestion[] = [
  {
    prompt: "What open work orders do we have right now?",
    tags: [
      { label: "work-orders", color: "red" },
      { label: "Work Orders API", color: "green" },
    ],
  },
  {
    prompt: "Do we have fiber splice trays and fusion splicers in stock?",
    tags: [
      { label: "inventory-check", color: "red" },
      { label: "Inventory MCP", color: "green" },
    ],
  },
  {
    prompt: "What is the procedure for emergency fiber cuts?",
    tags: [
      { label: "knowledge-retrieval", color: "red" },
      { label: "FoundryIQ", color: "green" },
    ],
  },
  {
    prompt:
      "I need to prepare for work order WO-001. What parts does it need and do we have them in stock?",
    tags: [
      { label: "cross-tool", color: "red" },
      { label: "Work Orders API", color: "green" },
      { label: "Inventory MCP", color: "yellow" },
    ],
  },
  {
    prompt: "Show me all critical priority work orders and who is assigned to them",
    tags: [
      { label: "work-orders", color: "red" },
      { label: "Work Orders API", color: "green" },
    ],
  },
  {
    prompt:
      "What safety guidelines should a technician follow for aerial fiber installation?",
    tags: [
      { label: "knowledge-retrieval", color: "red" },
      { label: "FoundryIQ", color: "green" },
    ],
  },
];

const tagColors = {
  red: "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300",
  green: "bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300",
  yellow:
    "bg-yellow-50 text-yellow-700 dark:bg-yellow-950 dark:text-yellow-300",
};

interface PromptSuggestionsProps {
  onSelect: (prompt: string) => void;
}

export default function PromptSuggestions({ onSelect }: PromptSuggestionsProps) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {suggestions.map((s, i) => (
        <button
          key={i}
          onClick={() => onSelect(s.prompt)}
          className="group rounded-xl border border-gray-200 bg-white p-4 text-left transition-shadow hover:shadow-md dark:border-gray-700 dark:bg-gray-900"
        >
          <p className="text-sm text-gray-800 group-hover:text-gray-950 dark:text-gray-200 dark:group-hover:text-white">
            {s.prompt}
          </p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {s.tags.map((tag, j) => (
              <span
                key={j}
                className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${tagColors[tag.color]}`}
              >
                {tag.label}
              </span>
            ))}
          </div>
        </button>
      ))}
    </div>
  );
}
