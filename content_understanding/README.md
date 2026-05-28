# Content Understanding Demo

This directory contains demo files and Azure Content Understanding (CU) tooling
for the Fibey Field Ops BUILD demo.

## Demo Files

| File | Purpose |
|---|---|
| `demo_files/fiber-splice-restoration.pdf` | Professional 2-page work order — primary demo document |
| `demo_files/scanned_work_order.png` | Handwritten/scanned work order |
| `demo_files/splicing-safety-cert.pdf` | Training certificate (non-work-order) — used to show classification routing |
| `demo_files/fiber-splice-restoration.json` | Expected CU extraction for the PDF |
| `demo_files/scanned_work_order.json` | Expected CU extraction for the PNG |

## CU Analyzer Setup (Two Steps)

The demo uses two CU analyzers with a strict dependency order.

### Step 1 — Create the Work Order Field Analyzer

```bash
uv run python content_understanding/tools/create_work_order_analyzer.py
```

Creates `cu_demo_work_order`: a custom analyzer that extracts structured fields
from work order documents (title, description, status, priority, assigned_technician,
location, due_date, parts_needed) aligned to the Fibey Work Orders API schema.

**Options:**
```bash
# Create and immediately test against the demo PDF:
uv run python content_understanding/tools/create_work_order_analyzer.py \
    --analyze content_understanding/demo_files/fiber-splice-restoration.pdf

# Test against an existing analyzer without recreating:
uv run python content_understanding/tools/create_work_order_analyzer.py \
    --analyze-only content_understanding/demo_files/scanned_work_order.png
```

### Step 2 — Create the Classify & Analyze Classifier

> **Requires Step 1 to be completed first.** The script will check for the
> `cu_demo_work_order` analyzer and exit with guidance if it is not found.

```bash
uv run python content_understanding/tools/create_classify_and_analyze.py
```

Creates `cu_demo_classify_and_analyze`: a classifier that categorizes an uploaded
document and routes it to the appropriate analyzer:

| Classified as | Routed to | Result |
|---|---|---|
| `work_order` | `cu_demo_work_order` | Structured field extraction |
| `other` | `prebuilt-layout` | General markdown extraction |

**Options:**
```bash
# Create and test against the work order PDF:
uv run python content_understanding/tools/create_classify_and_analyze.py \
    --analyze content_understanding/demo_files/fiber-splice-restoration.pdf

# Test against an existing classifier without recreating:
uv run python content_understanding/tools/create_classify_and_analyze.py \
    --analyze-only content_understanding/demo_files/splicing-safety-cert.pdf
```

## Demo Flow in the UI

The Activity sidebar has a **CU Context Provider** selector with three modes:

| Mode | Analyzer Used | Show This When... |
|---|---|---|
| **None** | — | No file upload needed |
| **Basic CU** | `prebuilt-layout` | General document → markdown |
| **Classify & Analyze Work Order** | `cu_demo_classify_and_analyze` | Show classification + routing |

**Recommended demo sequence:**
1. Upload `splicing-safety-cert.pdf` with **Classify & Analyze Work Order** → classified as `other`, routed to prebuilt-layout
2. Upload `fiber-splice-restoration.pdf` with **Basic CU** → raw markdown, no structure
3. Upload `fiber-splice-restoration.pdf` with **Classify & Analyze Work Order** → classified as `work_order`, structured fields extracted

## Environment

All tools load `.env` from the repository root automatically. No separate config needed.

```
AZURE_CONTENTUNDERSTANDING_ENDPOINT=https://<your-resource>.services.ai.azure.com/
```
