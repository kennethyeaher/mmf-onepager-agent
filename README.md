# MMF One Pager Agent

A local command line tool that turns deal notes and uploaded documents into a fund branded one page PDF investment brief. It runs the notes through Claude with web search to produce a structured sourcing brief in Markdown, then renders that Markdown into a Maryland Momentum Fund branded PDF with WeasyPrint.

## What it does

You drop a company's notes and any supporting documents into a folder. The tool reads everything in that folder, hands it to Claude as an analyst, and asks for a one page brief that separates founder stated claims from independently verified facts. The result is a maroon and gold one page PDF plus the Markdown it was built from.

The brief always includes an independent investor view: thesis, key risks, a bottom up market math estimate, open diligence questions, and a list of anything that could not be verified.

## Requirements

- Python 3.12
- A virtual environment at the repo root (`.venv`)
- WeasyPrint 69.0 with Pango and Cairo available (installed via Homebrew on macOS)
- An Anthropic API key with web search enabled by your org admin in the Console

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
  requirements.txt         pinned dependencies
  .env.example             template for your API key
  prompts/
    system_prompt.md       analyst role and brief format
  templates/
    template.html          fund branded one page template
  assets/
    fund_logo.png          fund logo, base64 embedded at render time
  src/
    __init__.py
    brief_agent.py         builds the brief by calling Claude
    renderer.py            fills the template and writes the PDF
    hubspot_client.py      dormant CRM client, off by default
  inputs/                  per company note folders, gitignored
  output/                  generated briefs, Markdown and PDF
```

## Branding notes

Page colors are set in the template, not pulled from the logo. The logo is read fresh and base64 embedded on every render, so swapping it requires no code change as long as the filename stays `assets/fund_logo.png`.

## Future steps

- HubSpot CRM integration is built but dormant. It will be re enabled behind a `--hubspot` flag once production CRM access is approved.
- Real fonts (Fraunces, Inter, JetBrains Mono) can be added later by dropping woff2 files into `assets/fonts/` and wiring up @font-face.