import html
import re
from pathlib import Path
from bs4 import BeautifulSoup


def batch_process_html_folder(input_folder="data/html_files", output_folder="data/txt_files"):
    """
    Finds all HTML files in `input_folder`, parses out garbage data while keeping
    questions intact, and saves the output as .txt files in `output_folder`.
    Prints individual and total question counts to the terminal.
    """
    input_path = Path(input_folder)
    output_path = Path(output_folder)

    output_path.mkdir(parents=True, exist_ok=True)

    html_files = list(input_path.glob("*.html")) + list(input_path.glob("*.htm"))

    if not html_files:
        print(f"No HTML files found in directory '{input_folder}'.")
        return

    print(f"Found {len(html_files)} HTML files to process...\n")

    total_questions = 0

    for file_path in html_files:
        output_txt_path = output_path / f"{file_path.stem}.txt"
        questions_in_file = parse_single_sanfoundry_file(file_path, output_txt_path)
        total_questions += questions_in_file

    print("\nBatch processing complete!")
    print(f"Total questions found across all files: {total_questions}")


def parse_single_sanfoundry_file(input_file, output_txt):
    with open(input_file, "r", encoding="utf-8") as f:
        raw_html = f.read()

    clean_html = html.unescape(raw_html)
    soup = BeautifulSoup(clean_html, "html.parser")

    for element in soup(
        ["script", "style", "nav", "header", "footer", "iframe", "ins", "form"]
    ):
        element.decompose()

    content_area = soup.find("div", class_="entry-content") or soup.body or soup

    raw_text = content_area.get_text(separator="\n")

    cleaned_lines = []
    ad_pattern = re.compile(r"^\s*advertisement\s*$", re.IGNORECASE)
    promo_pattern = re.compile(r"(free certifications|register now)", re.IGNORECASE)
    question_pattern = re.compile(r"^\d+\.\s+")

    question_count = 0

    for line in raw_text.splitlines():
        line_str = line.strip()

        if not line_str:
            continue

        if ad_pattern.match(line_str) or promo_pattern.search(line_str):
            continue

        if question_pattern.match(line_str):
            question_count += 1

        cleaned_lines.append(line_str)

    if cleaned_lines:
        output_txt.write_text("\n".join(cleaned_lines), encoding="utf-8")
        print(
            f"Successfully processed: '{output_txt.name}' ({question_count} questions found)"
        )
    else:
        print(f"Skipped '{input_file.name}': No text content found.")

    return question_count


if __name__ == "__main__":
    batch_process_html_folder(input_folder="data/html_files", output_folder="data/txt_files")
