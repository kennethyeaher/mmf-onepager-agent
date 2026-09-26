# MMF One Pager Agent

A local tool that turns deal notes and uploaded documents into a fund branded PDF investment brief. It runs the notes through Claude with web search to produce a structured sourcing brief in Markdown, then renders that Markdown into a Maryland Momentum Fund branded PDF with WeasyPrint.

## What it does

You drop a company's notes and any supporting documents into a folder, or paste them into the web app. The tool reads everything it is given, hands it to Claude as an analyst, and asks for a brief that separates founder stated claims from independently verified facts. The result is a maroon and gold branded PDF plus the Markdown it was built from.

The brief always includes an independent investor view: thesis, key risks, a bottom up market math estimate, open diligence questions, and a list of anything that could not be verified.

The tool runs two ways. The command line reads a per company inputs folder directly and is the fastest path for repeatable batches or free Markdown re renders. A local web app wraps the same pipeline in a full browser interface, so a non technical user can paste notes, attach a deck, pick a sector, and record a recommendation without touching a terminal beyond starting the server.

The web interface and files run locally. Brief generation sends supplied notes and documents to the Anthropic API and uses web search; it is not an offline workflow. Each user supplies their own account and API key.

## My contribution

I built the local brief workflow across the command line, Flask interface, PDF template, and saved brief library. Generated research still needs analyst review before use.

## Requirements

- Python 3.12
- Git
- An Anthropic API key with web search enabled by your org admin in the Console
- WeasyPrint 69.0, which needs Pango and Cairo on the system, not just from pip. The install path differs by operating system, covered in setup below
- Flask 3.1.3, only needed to run the web app, not the command line

---

## Step by step setup

Budget 20 to 30 minutes the first time. After that, starting the tool takes a few seconds.

### Step 1: Get an Anthropic API key

This is the credential that lets the tool talk to Claude, tied to your own account and your own billing.

1. Go to console.anthropic.com and sign in or create an account.
2. Add a payment method under Settings, Billing. Usage is pay as you go. Cost depends on the selected model, input size, and web search usage.
3. Go to Settings, API Keys, and click Create Key. Name it something like "MMF one pager tool."
4. Copy the key. It starts with `sk-ant-`. You will only see it once, so keep it somewhere safe for a moment. Never share this key or paste it into email, Slack, or chat.

### Step 2: Install Python and Git

Check whether you already have what you need before installing anything.

**macOS.** Open the Terminal app (search Spotlight for it), and run:

```bash
python3 --version
git --version
```

If both print a version number, move to Step 3. If either says command not found, install Homebrew first, then use it to install what is missing.

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python@3.12 git
```

**Windows.** Open PowerShell (search the Start menu for it), and run:

```powershell
python --version
git --version
```

If both print a version number, move to Step 3. If either is missing, install with winget, which comes built in on modern Windows:

```powershell
winget install Python.Python.3.12
winget install Git.Git
```

If winget is not available, download installers directly from python.org and git-scm.com instead. During the Python installer, check the box that says "Add python.exe to PATH" before clicking install, this matters, without it the next steps will not find Python. Close and reopen PowerShell after installing so it picks up the new programs.

### Step 3: Get the code

Choose a location, for example your Desktop, and download the code. This step is the same command on both operating systems, just run from Terminal on Mac or PowerShell on Windows.

```bash
cd ~/Desktop
git clone https://github.com/kennethyeaher/mmf-onepager-agent.git
cd mmf-onepager-agent
```

On Windows, `cd ~/Desktop` may not resolve the same way depending on your setup. If it fails, use the full path instead, for example `cd C:\Users\YourName\Desktop`.

### Step 4: Set up the Python environment and install dependencies

This creates an isolated space for the tool's dependencies so it does not interfere with anything else on your computer.

**macOS**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Your terminal prompt should now show `(.venv)` at the start of the line, that means the environment is active.

WeasyPrint, the piece that builds the PDF, needs a system library called Pango that does not come from pip:

```bash
brew install pango
```

**Windows**

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Your PowerShell prompt should now show `(.venv)` at the start of the line.

WeasyPrint needs the GTK3 runtime on Windows, which provides Pango and Cairo. This is the step most likely to need a second try. Download and run the GTK3 runtime installer for Windows, search "GTK3 runtime installer Windows" or use the installer maintained at github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer, run it with default options, then close and reopen PowerShell so it picks up the new libraries. If you still hit WeasyPrint errors after this, check WeasyPrint's own install documentation for the current Windows requirements, since these can shift between versions.

### Step 5: Add your API key

Both operating systems ship a template file, `.env.example`, that you copy and fill in.

**macOS**

```bash
cp .env.example .env
```

**Windows**

```powershell
Copy-Item .env.example .env
```

Then open the new `.env` file in any text editor (TextEdit, Notepad, VS Code) and set:

```
ANTHROPIC_API_KEY=sk-ant-your-real-key-here
```

Save and close. This file is gitignored on both platforms, so your key never gets committed or shared through the code.

### Step 6: Run it

With your environment active, meaning `(.venv)` shows in your prompt, run:

```bash
python app.py
```

You should see a message that it is running, something like `Running on http://127.0.0.1:5000`. Open a browser and go to that address. You should see the branded MMF sourcing brief tool.

### Step 7: Test it

Type a company name, paste in a sentence or two of test notes, and click Generate brief. It takes 30 to 90 seconds. When it finishes, a branded PDF should appear in the preview pane, downloadable from there. Check the sidebar too, your test brief should appear under Recent, and the full Brief Library view should list it.

---

## Using it going forward

Every time you want to use the tool, from inside the project folder:

**macOS**

```bash
cd ~/Desktop/mmf-onepager-agent
source .venv/bin/activate
python app.py
```

**Windows**

```powershell
cd ~\Desktop\mmf-onepager-agent
.venv\Scripts\activate
python app.py
```

Then open `http://127.0.0.1:5000` in your browser. When done, go back to the terminal or PowerShell window and press Control+C to stop the tool. Closing the browser tab alone does not stop it.

Every brief you generate is saved automatically in the `output` folder, both as a PDF and as the underlying Markdown, so nothing is lost between sessions.

---

## Troubleshooting

**"ModuleNotFoundError" when running `python app.py`.** Your terminal is not using the project's environment. Reactivate it (`source .venv/bin/activate` on Mac, `.venv\Scripts\activate` on Windows) from inside the `mmf-onepager-agent` folder, then confirm with:

```bash
python -c "import sys; print(sys.executable)"
```

The path it prints should end inside `mmf-onepager-agent\.venv`.

**WeasyPrint errors mentioning cairo or pango (macOS).** The system library from Step 4 did not install correctly. Re-run `brew install pango` and try again.

**WeasyPrint errors on Windows, or errors mentioning libgobject or similar.** The GTK3 runtime from Step 4 either did not install or PowerShell was not restarted afterward. Reinstall the runtime, then fully close and reopen PowerShell before trying again.

**The browser tab says it cannot connect.** The tool is not running. Go back to the terminal window and confirm you see the "Running on" message. If that window was closed, the tool stopped, restart it with the commands under "Using it going forward."

**"Address already in use," port 5000 taken.** The tool is already running in another window somewhere. Close it there first, or restart your computer.

**Windows only, "python is not recognized."** Python was installed without adding it to PATH. Reinstall Python from python.org and check "Add python.exe to PATH" during setup, or use `py` instead of `python` in the commands above, which is a launcher Windows installs separately.

---

## Command line usage

### Generate a brief from an inputs folder

Create a flat folder for the company under `inputs/`, for example `inputs/irob/`, and fill it with call notes, summaries, and any fund PDFs. Text and Markdown files are read inline as notes. PDFs are passed natively to the model.

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

API costs vary with the selected model, input size, and web search usage. To keep costs down:

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

![Decorative project banner: A local workspace for investment research.](docs/readme/footer.svg)

---

## Author

**Kenneth Yeaher**  
Master of Information Management  
University of Maryland, College Park  
[![LinkedIn: Kenneth Yeaher](https://img.shields.io/badge/LinkedIn-Kenneth_Yeaher-0A66C2?style=flat)](https://www.linkedin.com/in/kennethyeaher/)

`Python` · `Flask` · `Document Workflows`
