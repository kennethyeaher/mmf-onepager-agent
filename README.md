# MMF One Pager Agent

A local tool that turns deal notes and uploaded documents into a fund branded PDF investment brief. It runs the notes through Claude with web search to produce a structured sourcing brief in Markdown, then renders that Markdown into a Maryland Momentum Fund branded PDF with WeasyPrint.

## What it does

You drop a company's notes and any supporting documents into a folder, or paste them into the web app. The tool reads everything it is given, hands it to Claude as an analyst, and asks for a brief that separates founder stated claims from independently verified facts. The result is a maroon and gold branded PDF plus the Markdown it was built from.

The brief always includes an independent investor view: thesis, key risks, a bottom up market math estimate, open diligence questions, and a list of anything that could not be verified.

The tool runs two ways. The command line reads a per company inputs folder directly and is the fastest path for repeatable batches or free Markdown re renders. A local web app wraps the same pipeline in a full browser interface, so a non technical user can paste notes, attach a deck, pick a sector, and record a recommendation without touching a terminal beyond starting the server.

## Requirements

- Python 3.12
- A virtual environment at the repo root (`.venv`)
- WeasyPrint 69.0 with Pango and Cairo available (installed via Homebrew on macOS)
- An Anthropic API key with web search enabled by your org admin in the Console
- Flask 3.1.3, only needed to run the web app, not the command line

The tool is designed to run entirely on one machine. There is no hosted deployment, no shared server, and no shared key. Each user runs it locally against their own Anthropic account.

## Setup

Clone the repo and enter it:

```bash
git clone https://github.com/kennethyeaher/mmf-onepager-agent.git
cd mmf-onepager-agent
```

Create and activate a virtual environment, then install dependencies:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On macOS, WeasyPrint also needs Pango, which does not come from pip:

```bash
brew install pango
```

Copy the env template and add your key:

```bash
cp .env.example .env
```

Open `.env` and set `ANTHROPIC_API_KEY` to your real key. The `.env` file is gitignored and never gets committed.

## Usage

### Generate a brief from an inputs folder

Create a flat folder for the company under `inputs/`, for example `inputs/irob/`, and fill it with call notes, summaries, and any fund PDFs. Text and Markdown files are read inline as notes. PDFs are passed natively to the model.

Then run:

```bash
python main.py "Inception Robotics" --inputs inputs/irob
```

This calls the model, writes the brief Markdown to `output/`, and renders the branded PDF alongside it.

### Re render a PDF from edited Markdown

If you want to fix the sector, the recommendation, or any wording by hand, edit the Markdown in `output/` and re render with no model call:

```bash
python main.py "Inception Robotics" --render output/Inception_Robotics_onepager.md
```

This is the cheap path for overriding the model's judgment. It rebuilds the PDF from your edits without spending tokens.

### Web app

For most day to day use, run the browser version instead of the command line:

```bash
python app.py
```

Then open `http://127.0.0.1:5000`. The app binds to localhost only, so it is reachable from this machine and not the network.

The form covers the same inputs as the command line, plus a few things the command line does not have:

- A sector picker, single select from a fixed list of main labels plus an optional free text sub sector, pinned directly into the brief instead of left to the model to guess
- A recommendation picker, stamped into the rendered PDF as the team's recorded decision. When nothing is picked, the brief falls back to whatever the model itself concluded and labels it plainly as such
- Editable prepared by and contributing analyst fields for the PDF footer
- A single PDF deck upload for the data room
- A Brief Library and a Recent list in the sidebar, both reading from `output/index.json`, so every generated brief stays browsable with its sector, recorded recommendation, and how long ago it ran. Clicking a saved brief opens the PDF in a new tab

## Inputs folder convention

Each company gets its own flat subfolder under `inputs/`, holding files like:

- `call_notes.md`
- `zoom_summary.md`
- `deck_summary.md`
- any fund PDFs placed side by side

The `inputs/` folder is gitignored, so company notes are never committed.

## Supported input types

- Markdown and text: read inline as notes
- PDF: passed to the model as native document blocks

Office formats are not read directly. Export them to PDF or paste the text into a Markdown file.

## Brief library

Every brief generated through the web app is recorded in `output/index.json`, alongside the Markdown and PDF it produced. The index stores the display name, the sector shown on the brief, the recorded recommendation, and the save time. The web app reads this file to populate the Recent list in the sidebar and the full Brief Library view. A rerun of the same company overwrites its entry, so the library always reflects the latest run. Briefs generated before this file existed still appear, with a name derived from the PDF file name and no sector shown.

## Cost notes

Each brief runs roughly thirty to forty five cents depending on inputs. To keep costs down:

- Keep notes as pasted text or Markdown and reserve PDF for documents where tables or figures carry meaning
- Do not feed raw pitch decks, which are image heavy and can double the cost. Extract a deck once into a saved `deck_summary.md` and drop that in the folder instead
- Switch the model to a lighter one when deep judgment is not needed
- Lower the web search uses and the max tokens

## Project layout

```
mmf-onepager-agent/
  main.py                  entry point and command line handling
  app.py                    local web app entry point, Flask
  requirements.txt         pinned dependencies
  .env.example              template for your API key
  prompts/
    system_prompt.md       analyst role and brief format
  templates/
    template.html           fund branded PDF template
    index.html               web app page, distinct from the PDF template
  static/
    styles.css               web app styles
    app.js                    web app front end script
  assets/
    fund_logo.png           fund logo, base64 embedded at render time
  src/
    __init__.py
    brief_agent.py           builds the brief by calling Claude
    renderer.py               fills the template and writes the PDF
    library.py                brief library index, reads and writes output/index.json
    hubspot_client.py        dormant CRM client, off by default
  inputs/                    per company note folders, gitignored
  output/                    generated briefs, Markdown, PDF, and the library index
```

## Branding notes

Page colors are set in the template, not pulled from the logo. The logo is read fresh and base64 embedded on every render, so swapping it requires no code change as long as the filename stays `assets/fund_logo.png`.

## Future steps

- Multi file data room. `build_brief`'s `pdf_paths` already accepts a list, most of the remaining work is on the web app upload form.
- Save draft, a persistence layer for in progress form state before a brief is generated.
- A streaming progress bar in the web app, replacing the current indeterminate spinner with real step by step status.
- HubSpot CRM integration is built but dormant. It will be re enabled behind a `--hubspot` flag once production CRM access is approved.
- Real fonts (Fraunces, Inter, JetBrains Mono) can be added later by dropping woff2 files into `assets/fonts/` and wiring up @font-face.