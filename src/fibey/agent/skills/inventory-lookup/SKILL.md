---
name: inventory-lookup
description: Handle inventory and parts queries — stock checks, part lookups, availability, category browsing, and equipment searches. Use when the technician asks about parts, stock levels, SKUs, availability, supplies, or equipment.
---

# Inventory Lookup

Use this skill when the technician asks about parts, stock, equipment, or availability.

## When to Use

- "Do we have any SC connectors?"
- "What's the stock on FIB-042?"
- "Show me all splice equipment"
- "Is the OTDR available?"
- "What connectors do we carry?"
- "Check stock for the parts on WO-007"

## Step-by-Step Instructions

### Step 1: Choose the Right Tool

| Question Type | Tool to Use | Example |
|--------------|-------------|---------|
| Free-text search ("do we have…", "find…") | `search_parts` | "do we have splice trays?" |
| Browse by category | `list_parts` with `category` filter | "show all connectors" |
| Specific part by ID | `get_part_details` with `part_id` | "details on FIB-012" |
| Stock level for a known part | `check_stock` with `part_id` | "how many FIB-042 in stock?" |
| Stock levels for multiple parts | `check_stock_batch` with `part_ids` list | "check stock for FIB-003 and FIB-012" |

**Categories available:** Connectors, Cables, Splitters, Splice Equipment, Test Equipment

### Step 2: Format the Response

**For a single part:**
```
**FIB-042 — SC/APC Connector** 🟢 In Stock
- **SKU:** CONN-SC-APC-500
- **Stock:** 342 units (Warehouse A)
- **Price:** $4.50/unit
- **Manufacturer:** Corning
```

**For multiple parts (2+), ALWAYS use a table with status indicators:**

```
### Inventory Results

| Part | Stock | Status | Location |
|------|-------|--------|----------|
| SC Connector (FIB-012) | 342 | 🟢 In Stock | WH-A1 |
| LC Connector (FIB-015) | 12 | 🟡 Low Stock | WH-B2 |
| Splice Tray (FIB-023) | 0 | 🔴 Out of Stock | — |

> 🟡 **Note:** LC Connectors are running low — consider reordering.
```

**CRITICAL:** When checking multiple items, always use a markdown table. Never
list items as a plain paragraph. Separate different topics with `---` dividers
or `###` headers.

### Step 3: Interpret Stock Status

Always show a status indicator:
- 🟢 **In Stock** — quantity is above minimum threshold
- 🟡 **Low Stock** — quantity is at or below minimum threshold but > 0. Add: _"Stock is running low — consider reordering."_
- 🔴 **Out of Stock** — quantity is 0. Add: _"Currently unavailable. Check with supply chain for restock ETA."_

### Step 4: Provide Actionable Next Steps

- If stock is low or out: suggest reordering or checking alternatives
- If the technician seems to be prepping for a job: offer to check a work order's full parts list
- If they searched broadly: ask if they need details on a specific part

## What NOT to Do

- ❌ Do not guess stock quantities — always use the inventory tools
- ❌ Do not skip the stock status indicator
- ❌ Do not use knowledge base tools for inventory questions
- ❌ Do not invent part IDs or SKUs
- ❌ Do not list multiple items as a flat paragraph — always use tables
