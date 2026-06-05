"""
MMF one pager agent. Command line entry point.

Ties the package together: read a per company inputs folder, write the brief
with Claude and web search, save the Markdown, and render the branded PDF.

The inputs folder holds everything gathered for one company, side by side.
Text and Markdown files are read inline as notes. PDF files are passed to the
model as documents. Other file types are skipped with a warning.

Run it like this:
    python main.py "HighT-Tech" --inputs inputs/htt
"""

import argparse
import re
from pathlib import Path

from dotenv import load_dotenv

from src import brief_agent, renderer

# Resolve paths from the package root so the tool runs from any directory.
BASE_DIR = Path(__file__).resolve().parent

# Default locations for the prompt and the output folder.
PROMPT_PATH = BASE_DIR / "prompts" / "system_prompt.md"
OUTPUT_DIR = BASE_DIR / "output"

# File extensions read inline as notes, and the extension sent as a document.
TEXT_TYPES = (".md", ".txt")
PDF_TYPE = ".pdf"


def read_inputs(folder):
    """
    Read every file in a company inputs folder and sort it by type.

    Text and Markdown files are concatenated into one notes string, each
    labeled with its file name so the model can tell sources apart. PDF files
    are collected as paths to be sent as document blocks. Other file types are
    skipped with a warning.

    Parameters
    folder : str
        Path to the per company inputs folder.

    Returns
    notes_text : str
        The text and Markdown inputs, each under a file name label.
    pdf_paths : list
        Paths to the PDF files found in the folder.

    Raises
    FileNotFoundError
        If the folder does not exist.
    """
    input_dir = Path(folder)
    if not input_dir.is_dir():
        raise FileNotFoundError(f"inputs folder not found: {folder}")

    note_blocks = []
    pdf_paths = []

    # Walk the folder in name order so runs are repeatable.
    for item in sorted(input_dir.iterdir()):
        if not item.is_file():
            continue
        suffix = item.suffix.lower()

        # Read text and Markdown inline, labeled by file name.
        if suffix in TEXT_TYPES:
            text = item.read_text(encoding="utf-8").strip()
            if text:
                note_blocks.append(f"--- {item.name} ---\n{text}")
        # Collect PDFs to send as document blocks.
        elif suffix == PDF_TYPE:
            pdf_paths.append(item)
        # Skip anything else so an unsupported file does not break the run.
        else:
            print(f"   Skipping unsupported file: {item.name}")

    notes_text = "\n\n".join(note_blocks)
    return notes_text, pdf_paths


def save_markdown(company_name, brief, out_dir):
    """
    Save the brief as a Markdown file.

    Parameters
    company_name : str
        The company name, used to build the file name.
    brief : str
        The brief as Markdown.
    out_dir : str
        Folder to write into.

    Returns
    md_path : Path
        Path to the saved Markdown file.
    """
    safe_name = re.sub(r"[^A-Za-z0-9]+", "_", company_name).strip("_") or "company"
    out_path = Path(out_dir)
    out_path.mkdir(exist_ok=True)
    md_path = out_path / f"{safe_name}_onepager.md"
    md_path.write_text(brief, encoding="utf-8")
    return md_path


def main():
    """
    Parse arguments, run the pipeline, and report where the files were saved.

    Parameters
    none

    Returns
    none
    """
    # Load ANTHROPIC_API_KEY from the .env file before the agent runs.
    load_dotenv()

    parser = argparse.ArgumentParser(description="Generate a branded VC sourcing one pager.")
    parser.add_argument("company", help="Company name, shown as the headline")
    parser.add_argument("--inputs", required=True,
                        help="Path to the per company inputs folder")
    parser.add_argument("--prompt", default=PROMPT_PATH,
                        help="Path to the instruction template")
    args = parser.parse_args()

    # Load the prompt and the company inputs.
    system_prompt = Path(args.prompt).read_text(encoding="utf-8")
    notes_text, pdf_paths = read_inputs(args.inputs)
    print(f"-> Read {len(notes_text.split('---')) - 1 if notes_text else 0} note file(s) "
          f"and {len(pdf_paths)} PDF(s) from {args.inputs}")

    # Write the brief with Claude and web search.
    print("-> Running Claude with web search. This can take 30 to 90 seconds...")
    brief = brief_agent.build_brief(args.company, notes_text, pdf_paths, system_prompt)

    # Save the Markdown and render the branded PDF.
    md_path = save_markdown(args.company, brief, OUTPUT_DIR)
    print(f"-> Saved {md_path}")
    try:
        pdf_path = renderer.render_pdf(brief, args.company, OUTPUT_DIR)
        print(f"-> Branded PDF: {pdf_path}")
    except Exception as error:
        # Surface the real error instead of hiding it. The Markdown is still saved.
        print(f"   PDF render failed: {error!r}. The Markdown is saved.")


if __name__ == "__main__":
    main()