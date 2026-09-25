import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import re
import threading
import time
import requests

LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
MAX_WORKERS = 3  

file_lock = threading.Lock()


def reconstruct_question_with_llm(raw_question_text, max_retries=3):
    """Sends raw text to LM Studio to structure into clean JSON."""
    system_prompt = (
        "You are an expert Python code parser. Clean up raw MCQ text extracted from HTML. "
        "Reconstruct broken Python code into valid code snippets. "
        "Return ONLY a valid JSON object with no markdown wrappers."
    )

    user_prompt = f"""
    Fix and parse the following MCQ into a clean JSON structure:

    {raw_question_text}

    JSON Schema required:
    {{
      "topic": "Topic name if available, else 'Python'",
      "question_text": "Main question string",
      "code_snippet": "Reconstructed code block or empty string if no code",
      "options": ["a) choice 1", "b) choice 2", "c) choice 3", "d) choice 4"],
      "answer": "Correct option letter (e.g. 'a')",
      "explanation": "Explanation string"
    }}
    """

    payload = {
        "model": "qwen2.5-coder-7b-instruct-q4_k_m.gguf",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(LM_STUDIO_URL, json=payload, timeout=120)

            if response.status_code != 200:
                time.sleep(2)
                continue

            res_data = response.json()

            if "choices" in res_data and len(res_data["choices"]) > 0:
                content = res_data["choices"][0]["message"]["content"].strip()

                # Clean markdown code block wrappers
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]

                return json.loads(content.strip())

        except (requests.exceptions.RequestException, json.JSONDecodeError):
            time.sleep(2)

    return None


def sanitize_tsv_text(text):
    """Strips tab characters to protect TSV layout integrity during Anki import."""
    if not text:
        return ""
    # Replace tabs with spaces so Anki doesn't create unwanted extra columns
    return text.replace("\t", " ")


def format_for_anki(data):
    """Converts JSON data into styled Anki Front and Back HTML fields."""
    topic = data.get("topic", "Python")
    q_text = data.get("question_text", "")
    code = data.get("code_snippet", "").strip()
    options = data.get("options", [])
    answer = data.get("answer", "").strip().upper()
    explanation = data.get("explanation", "")

    front_parts = [f"<div class='topic'>{topic}</div>"]
    front_parts.append(f"<div class='question-text'>{q_text}</div>")

    if code:
        front_parts.append(f"<pre><code class='language-python'>{code}</code></pre>")

    if options:
        options_html = "".join([f"<li>{opt}</li>" for opt in options])
        front_parts.append(f"<ul class='options'>{options_html}</ul>")

    front_html = "\n".join(front_parts)

    back_parts = [f'<div class="answer-key"><b>Correct Answer:</b> {answer}</div>']
    if explanation:
        back_parts.append(f'<div class="explanation">{explanation}</div>')

    back_html = "\n".join(back_parts)

    return sanitize_tsv_text(front_html), sanitize_tsv_text(back_html)


def process_single_chunk(chunk):
    """Processes a single question chunk and returns formatted front/back fields."""
    parsed_json = reconstruct_question_with_llm(chunk)
    if parsed_json:
        return format_for_anki(parsed_json)
    return None


def append_card_to_tsv(output_path, front, back):
    """Safely writes a single card to the TSV file using thread locking."""
    with file_lock:
        with open(output_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow([front, back])


def load_processed_files(log_path):
    """Reads completed file names from tracking log to support script resumes."""
    if log_path.exists():
        return set(log_path.read_text(encoding="utf-8").splitlines())
    return set()


def log_file_completed(log_path, file_name):
    """Logs a completed file name to prevent re-processing on restarts."""
    with file_lock:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"{file_name}\n")


def batch_process_txt_folder(
    input_folder="data/txt_files",
    output_file="output/anki_import_all.tsv",
    log_file="output/processed_files.log",
):
    input_path = Path(input_folder)
    output_path = Path(output_file)
    log_path = Path(log_file)

    txt_files = list(input_path.glob("*.txt"))
    total_files = len(txt_files)

    if not txt_files:
        print(f"No .txt files found in '{input_folder}'.")
        return

    processed_files = load_processed_files(log_path)
    remaining_files = [f for f in txt_files if f.name not in processed_files]

    print(
        f"Found {total_files} total file(s). ({len(processed_files)} already completed, {len(remaining_files)} remaining)\n"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    for index, file_path in enumerate(remaining_files, start=1):
        print(f"[{index}/{len(remaining_files)}] Processing file: '{file_path.name}'")
        content = file_path.read_text(encoding="utf-8")

        chunks = [
            c.strip()
            for c in re.split(r"\n(?=\d+\.\s+)", content)
            if c.strip() and re.match(r"^\d+\.\s+", c.strip())
        ]

        file_cards = 0
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_chunk = {
                executor.submit(process_single_chunk, chunk): chunk for chunk in chunks
            }

            for future in as_completed(future_to_chunk):
                result = future.result()
                if result:
                    front, back = result
                    append_card_to_tsv(output_path, front, back)
                    file_cards += 1

        log_file_completed(log_path, file_path.name)
        print(f"Completed '{file_path.name}': {file_cards} cards written to TSV.\n")

    print("=" * 50)
    print("Batch processing complete!")
    print(f"Output saved to: '{output_path.resolve()}'")
    print("=" * 50)


if __name__ == "__main__":
    batch_process_txt_folder()
