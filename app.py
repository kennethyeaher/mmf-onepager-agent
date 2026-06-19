"""
MMF one pager agent. Local web entry point.

A small browser app so a non technical user can generate a brief without the
terminal. It serves a branded single page from the templates folder, takes a
company name, pasted notes, and an optional deck PDF, runs the same pipeline
the command line uses, and returns the branded PDF to the page.

This server binds to localhost only, so it is reachable from this machine and
not from the network. Run it with:
    python app.py
then open http://127.0.0.1:5000 in a browser.

Required environment variable:
    ANTHROPIC_API_KEY : an Anthropic API key, loaded from the .env file
"""

import re
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, request, send_file, render_template

from src import brief_agent, renderer

# Resolve paths from the package root so the tool runs from any directory.
BASE_DIR = Path(__file__).resolve().parent

# Default locations for the prompt, the output folder, and the brand logo.
PROMPT_PATH = BASE_DIR / "prompts" / "system_prompt.md"
OUTPUT_DIR = BASE_DIR / "output"
LOGO_PATH = BASE_DIR / "assets" / "fund_logo.png"

# Load ANTHROPIC_API_KEY from the .env file before any request runs.
load_dotenv()

# Serve templates from templates and static assets from static, the defaults.
app = Flask(__name__)


def save_markdown(company_name, brief, out_dir):
    """
    Save the brief as a Markdown file for the audit trail.

    Mirrors the saver the command line uses so a generated brief can be edited
    by hand and rebuilt later with the render only mode.

    Parameters
    company_name : str
        The company name, used to build the file name.
    brief : str
        The brief as Markdown.
    out_dir : Path
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


@app.route("/")
def home():
    """
    Serve the single page app.

    Parameters
    none

    Returns
    html : str
        The rendered page.
    """
    return render_template("index.html")


@app.route("/logo.png")
def logo():
    """
    Serve the fund logo to the browser.

    The renderer embeds the logo in the PDF as base64, but the web page needs
    it as a normal image request, so this route hands back the same asset.

    Parameters
    none

    Returns
    response
        The logo image file.
    """
    return send_file(str(LOGO_PATH), mimetype="image/png")


@app.route("/generate", methods=["POST"])
def generate():
    """
    Run the pipeline from the submitted form and return the branded PDF.

    Reads the company name, the pasted notes, and an optional deck PDF from the
    form. Wraps the notes in the same label format the folder reader produces,
    runs the agent and renderer unchanged, saves the Markdown for the record,
    and sends the PDF back to the page.

    Parameters
    none

    Returns
    response
        The PDF file, or a short error page on failure.
    """
    # Read the form fields. The deck file is optional.
    company_name = (request.form.get("company") or "").strip()
    notes = (request.form.get("notes") or "").strip()
    sector_main = (request.form.get("sector_main") or "").strip()
    sector_sub = (request.form.get("sector_sub") or "").strip()
    prepared_by = (request.form.get("prepared_by") or "").strip()
    analyst = (request.form.get("analyst") or "").strip()
    recommendation = (request.form.get("recommendation") or "").strip()
    deck = request.files.get("deck")

    if not company_name:
        return "Please enter a company name.", 400

    # Wrap the pasted notes in the same label the folder reader uses so the
    # agent sees inputs in the shape the system prompt expects.
    notes_text = f"--- pasted notes ---\n{notes}" if notes else ""

    # Save an uploaded deck to a temp PDF so it can be passed as a document.
    pdf_paths = []
    temp_pdf = None
    if deck and deck.filename.lower().endswith(".pdf"):
        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        deck.save(temp_pdf.name)
        pdf_paths.append(Path(temp_pdf.name))

    # Run the agent and renderer, then hand back the PDF. Any failure returns a
    # short message instead of a stack trace in the browser.
    try:
        system_prompt = Path(PROMPT_PATH).read_text(encoding="utf-8")
        brief = brief_agent.build_brief(company_name, notes_text, pdf_paths, system_prompt, sector_main, sector_sub)
        save_markdown(company_name, brief, OUTPUT_DIR)
        # Record the picked decision as a team decision, or leave the
        # recommendation to the model when nothing was picked.
        recommendation_label = f"{recommendation.capitalize()} (team)" if recommendation else ""
        pdf_path = renderer.render_pdf(
            brief, company_name, OUTPUT_DIR,
            prepared_by=prepared_by, analyst=analyst,
            recommendation=recommendation_label,
        )
        # Name the response so the browser saves it like the command line does,
        # for example Activate_onepager.pdf instead of a generic Unknown name.
        return send_file(str(pdf_path), as_attachment=False, download_name=pdf_path.name)
    except Exception as error:
        return f"Generation failed: {error!r}", 500
    finally:
        # Remove the temp deck file whether or not the run succeeded.
        if temp_pdf is not None:
            Path(temp_pdf.name).unlink(missing_ok=True)


# Bind to localhost only so the page is reachable from this machine and not the
# wider network. Debug is off so the interactive debugger is never exposed.
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)