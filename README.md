# Sanfoundry MCQ to Anki Converter

An automated pipeline designed to extract Python Multiple Choice Questions (MCQs) from raw Sanfoundry HTML pages, structure broken code snippets using a local Large Language Model (LLM via LM Studio), and format the output into an Anki-ready `.tsv` import file.

---

## Pipeline Overview

```
[ data/html_files/ ] ──( 01_extract_questions.py )──> [ data/txt_files/ ] ──( 02_generate_anki_cards.py + Local LLM )──> [ output/anki_import_all.tsv ]
```

1. **HTML Extraction (`01_extract_questions.py`)**: Strips advertisements, navigation elements, headers, and footers from downloaded HTML pages, extracting raw question sections into individual `.txt` files in `data/txt_files/`.
2. **AI Formatting (`02_generate_anki_cards.py`)**: Queries a local LLM running in LM Studio using multithreading to fix code indentation, parse options, isolate correct answers/explanations, and format each question into styled Anki Front/Back HTML fields saved to `output/anki_import_all.tsv`.
3. **Log & Resume (`output/processed_files.log`)**: Tracks completed files so batch processing can be paused and resumed without duplicating effort.

---

## Directory Structure

```text
.
├── data/
│   ├── html_files/         # Input: Raw Sanfoundry HTML pages
│   └── txt_files/          # Intermediate: Cleaned question text files
├── output/
│   ├── anki_import_all.tsv # Output: Formatted Anki flashcard batch file
│   └── processed_files.log # Progress tracking log (auto-generated)
├── 01_extract_questions.py  # Step 1: HTML parsing & text extraction
├── 02_generate_anki_cards.py# Step 2: Local LLM integration & Anki TSV generator
└── README.md
```

---

## Features

- **Automated Text Extraction**: Cleans raw HTML pages downloaded using browser extensions (e.g., SingleFile) and extracts target MCQ sections.
- **Local AI Structuring**: Uses a locally hosted LLM (e.g., Qwen2.5-Coder-7B) to fix broken Python syntax, construct valid code blocks, and output structured JSON.
- **Concurrent Processing**: Utilizes `ThreadPoolExecutor` in `02_generate_anki_cards.py` for faster batch processing across multiple requests.
- **Fail-Safe & Resume**: Maintains `output/processed_files.log` and uses thread locking (`threading.Lock`) to safely append rows to the TSV file without corruption or re-processing on restarts.
- **Anki-Ready Styling**: Generates HTML with predefined classes (`.topic`, `.question-text`, `.options`, `.answer-key`, `.explanation`) for custom Anki card styling.

---

## Prerequisites

### 1. Python Dependencies

Install the required Python packages:

```bash
pip install beautifulsoup4 requests
```

### 2. LM Studio Setup

1. Download and install [LM Studio](https://lmstudio.ai/).
2. Download a coding-capable model such as `qwen2.5-coder-7b-instruct-q4_k_m.gguf`.
3. Start the **Local Inference Server** in LM Studio on port `1234` (`http://localhost:1234`).
4. Ensure the server API endpoints are active (OpenAI-compatible chat completions enabled).

---

## How to Use

### Step 1: Prepare HTML Files
Save your target Sanfoundry HTML files into the `data/html_files/` directory.

### Step 2: Extract Question Text
Run `01_extract_questions.py` to strip webpage noise and extract raw MCQ text into `.txt` files:

```bash
python 01_extract_questions.py
```
*Outputs generated `.txt` files to `data/txt_files/`.*

### Step 3: Generate Anki Cards with Local AI
Ensure your LM Studio local server is running, then execute `02_generate_anki_cards.py`:

```bash
python 02_generate_anki_cards.py
```
*Appends formatted cards to `output/anki_import_all.tsv` and logs completed files to `output/processed_files.log`.*

---

## Importing into Anki

1. Open **Anki** and click **Import File**.
2. Select `output/anki_import_all.tsv`.
3. Set the following import options:
   - **Type**: Basic (or a custom note type matching your styling preferences).
   - **Fields separated by**: `Tab`.
   - **Allow HTML in fields**: `Checked / Enabled`.
   - **Field Mapping**:
     - Field 1 -> `Front`
     - Field 2 -> `Back`
4. Click **Import**.

---

## Customization

You can adjust processing parameters inside `02_generate_anki_cards.py`:

- **LM Studio Endpoint**: Change `LM_STUDIO_URL` if your local server runs on a different port.
- **Model Name**: Update `payload["model"]` to match the model identifier loaded in your LM Studio instance.
- **Thread Count**: Modify `MAX_WORKERS` to increase or decrease parallel API requests depending on your hardware capacity.