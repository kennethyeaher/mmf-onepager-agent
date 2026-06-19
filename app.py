"""
MMF one pager agent. Local web entry point.

A small browser form so a non technical user can generate a brief without the
terminal. It wraps the same pipeline the command line uses. Paste notes, drop
an optional deck PDF, click Generate, and get the branded PDF back. The agent
and renderer are reused unchanged from the src package.

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
from flask import Flask, request, send_file, render_template_string

from src import brief_agent, renderer

# Resolve paths from the package root so the tool runs from any directory.
BASE_DIR = Path(__file__).resolve().parent

# Default locations for the prompt and the output folder.
PROMPT_PATH = BASE_DIR / "prompts" / "system_prompt.md"
OUTPUT_DIR = BASE_DIR / "output"

# Load ANTHROPIC_API_KEY from the .env file before any request runs.
load_dotenv()

app = Flask(__name__)


# The single page form. Kept inline so the web layer stays one file. The form
# posts to a new tab so the PDF opens there and this form tab survives. The
# submit handler shows a spinner and a waiting line and blocks a double submit.
# When this tab regains focus the form resets so another brief can be run.
FORM_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>MMF Sourcing Brief</title>
<style>
  body { font-family: Helvetica, Arial, sans-serif; color: #211C18; background: #FCFAF5;
         max-width: 720px; margin: 40px auto; padding: 0 20px; }
  h1 { font-family: Georgia, serif; color: #7C1D2B; font-size: 22px; margin-bottom: 4px; }
  p.sub { color: #6E665B; margin-top: 0; }
  label { display: block; font-weight: bold; margin: 18px 0 6px; }
  input[type=text], textarea { width: 100%; padding: 8px; border: 1px solid #D8D0C0;
         border-radius: 4px; font-size: 14px; box-sizing: border-box; }
  textarea { height: 280px; resize: vertical; }
  button { margin-top: 20px; background: #7C1D2B; color: #fff; border: none;
         border-radius: 4px; padding: 10px 20px; font-size: 15px; cursor: pointer; }
  button:disabled { background: #999; cursor: default; }
  .note { color: #6E665B; font-size: 13px; margin-top: 12px; }
  .spinner { display: none; width: 16px; height: 16px; vertical-align: middle;
         margin-right: 8px; border: 2px solid #D8D0C0; border-top-color: #7C1D2B;
         border-radius: 50%; animation: spin 0.8s linear infinite; }
  .spinner.on { display: inline-block; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>
  <h1>Maryland Momentum Fund</h1>
  <p class="sub">Investment Sourcing Brief generator</p>

  <form method="post" action="/generate" enctype="multipart/form-data" target="_blank" onsubmit="onGenerate()">
    <label for="company">Company name</label>
    <input type="text" id="company" name="company" placeholder="Inception Robotics" required>

    <label for="notes">Notes</label>
    <textarea id="notes" name="notes" placeholder="Paste call notes, CRM notes, and any context here"></textarea>

    <label for="deck">Pitch deck PDF (optional)</label>
    <input type="file" id="deck" name="deck" accept="application/pdf">

    <button id="go" type="submit">Generate brief</button>
    <p class="note"><span class="spinner" id="spin"></span><span id="status"></span></p>
  </form>

  <script>
    // Show a spinner and a waiting message and block a double submit while the
    // brief runs. The PDF opens in a new tab, so this tab keeps the form.
    function onGenerate() {
      document.getElementById("go").disabled = true;
      document.getElementById("go").textContent = "Generating...";
      document.getElementById("spin").classList.add("on");
      document.getElementById("status").textContent =
        "Working. This can take up to 90 seconds. The PDF opens in a new tab when it is ready.";
    }

    // Reset the form when this tab regains focus so another brief can be run.
    // Generation finishes in the new tab, so returning here is the signal to
    // enable the button again and clear the waiting state.
    function resetForm() {
      var go = document.getElementById("go");
      if (!go.disabled) {
        return;
      }
      go.disabled = false;
      go.textContent = "Generate brief";
      document.getElementById("spin").classList.remove("on");
      document.getElementById("status").textContent = "";
    }

    // Listen for both window focus and tab visibility so the reset fires
    // whether the user switches tabs or switches windows.
    window.addEventListener("focus", resetForm);
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "visible") {
        resetForm();
      }
    });
  </script>
</body>
</html>"""


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
    Serve the input form.

    Parameters
    none

    Returns
    html : str
        The rendered form page.
    """
    return render_template_string(FORM_HTML)


@app.route("/generate", methods=["POST"])
def generate():
    """
    Run the pipeline from the submitted form and return the branded PDF.

    Reads the company name, the pasted notes, and an optional deck PDF from the
    form. Wraps the notes in the same label format the folder reader produces,
    runs the agent and renderer unchanged, saves the Markdown for the record,
    and sends the PDF back to the browser.

    Parameters
    none

    Returns
    response
        The PDF file shown in the browser, or a short error page on failure.
    """
    # Read the form fields. The deck file is optional.
    company_name = (request.form.get("company") or "").strip()
    notes = (request.form.get("notes") or "").strip()
    deck = request.files.get("deck")

    if not company_name:
        return "Please enter a company name. <a href='/'>Back</a>", 400

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
        brief = brief_agent.build_brief(company_name, notes_text, pdf_paths, system_prompt)
        save_markdown(company_name, brief, OUTPUT_DIR)
        pdf_path = renderer.render_pdf(brief, company_name, OUTPUT_DIR)
        return send_file(str(pdf_path), as_attachment=False)
    except Exception as error:
        return f"Generation failed: {error!r}. <a href='/'>Back</a>", 500
    finally:
        # Remove the temp deck file whether or not the run succeeded.
        if temp_pdf is not None:
            Path(temp_pdf.name).unlink(missing_ok=True)


# Bind to localhost only so the form is reachable from this machine and not the
# wider network. Debug is off so the interactive debugger is never exposed.
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)