"""
MMF one pager agent. Command line entry point.

Two modes. The default reads a per company inputs folder, writes the brief with
Claude and web search, saves the Markdown, and renders the branded PDF. The
render mode skips the model entirely and rebuilds the PDF from a Markdown file
you have already generated and edited by hand, so fixing a sector, a
recommendation, or any wording costs nothing.

The inputs folder holds everything gathered for one company, side by side.
Text and Markdown files are read inline as notes. PDF files are passed to the
model as documents. Other file types are skipped with a warning.

Run it like this:
    python main.py "Inception Robotics" --inputs inputs/irob
    python main.py "Inception Robotics" --render output/Inception_Robotics_onepager.md
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


def run_pipeline(company_name, inputs_folder, prompt_path):
    """
    Run the full pipeline: read inputs, write the brief, save it, render it.

    Parameters
    company_name : str
        The company to research, shown as the headline.
    inputs_folder : str
        Path to the per company inputs folder.
    prompt_path : str
        Path to the instruction template.

    Returns
    none
    """
    # Load the prompt and the company inputs.
    system_prompt = Path(prompt_path).read_text(encoding="utf-8")
    notes_text, pdf_paths = read_inputs(inputs_folder)
    note_count = len(notes_text.split("---")) - 1 if notes_text else 0
    print(f"-> Read {note_count} note file(s) and {len(pdf_paths)} PDF(s) "
          f"from {inputs_folder}")

    # Write the brief with Claude and web search.
    print("-> Running Claude with web search. This can take 30 to 90 seconds...")
    brief = brief_agent.build_brief(company_name, notes_text, pdf_paths, system_prompt)

    # Save the Markdown, then render the branded PDF from it.
    md_path = save_markdown(company_name, brief, OUTPUT_DIR)
    print(f"-> Saved {md_path}")
    render_from_markdown(company_name, md_path)


def render_from_markdown(company_name, md_path):
    """
    Render a branded PDF from an existing Markdown file, with no model call.

    Use this to rebuild the PDF after editing the Markdown by hand, for example
    to change the sector or the recommendation. It is free because it never
    calls the model.

    Parameters
    company_name : str
        The company name, shown as the headline.
    md_path : str
        Path to the Markdown file to render.

    Returns
    none

    Raises
    FileNotFoundError
        If the Markdown file does not exist.
    """
    source = Path(md_path)
    if not source.is_file():
        raise FileNotFoundError(f"markdown file not found: {md_path}")

    brief = source.read_text(encoding="utf-8")
    try:
        pdf_path = renderer.render_pdf(brief, company_name, OUTPUT_DIR)
        print(f"-> Branded PDF: {pdf_path}")
    except Exception as error:
        # Surface the real error instead of hiding it. The Markdown is untouched.
        print(f"   PDF render failed: {error!r}. The Markdown is untouched.")


def main():
    """
    Parse arguments and run either the full pipeline or a render only rebuild.

    Parameters
    none

    Returns
    none
    """
    # Load ANTHROPIC_API_KEY from the .env file before the agent runs.
    load_dotenv()

    parser = argparse.ArgumentParser(description="Generate a branded VC sourcing one pager.")
    parser.add_argument("company", help="Company name, shown as the headline")
    parser.add_argument("--inputs",
                        help="Path to the per company inputs folder")
    parser.add_argument("--render",
                        help="Path to an existing Markdown file to rebuild as a PDF, no model call")
    parser.add_argument("--prompt", default=PROMPT_PATH,
                        help="Path to the instruction template")
    args = parser.parse_args()

    # Render mode rebuilds the PDF from an edited Markdown file for free.
    if args.render:
        render_from_markdown(args.company, args.render)
        return

    # Otherwise run the full pipeline, which needs an inputs folder.
    if not args.inputs:
        parser.error("provide --inputs to generate a brief, or --render to rebuild from Markdown")
    run_pipeline(args.company, args.inputs, args.prompt)


if __name__ == "__main__":
    main()