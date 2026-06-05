"""
Renderer.

Turns the Markdown brief into the branded one pager PDF. This step is fully
mechanical, so it adds no model cost. It reads the labeled front lines off the
top of the brief, sorts each section into the sidebar or the main column, drops
everything into the HTML template, and writes a branded HTML file and a PDF.

Layout contract for the Markdown the agent produces:
    The brief opens with labeled lines SECTOR, RECOMMENDATION, and SOURCES, one
    per line. Text after those lines and before the first "## " heading becomes
    the lead paragraph. Sections whose heading contains "quick facts" or
    "traction" go in the left sidebar. The "investor view" section becomes a
    full width band at the bottom. Every other section goes in the main column.

The fund logo is embedded as base64 so the PDF never has a broken image link.
A per company logo is intentionally not handled here yet. That hook is added in
main.py later.
"""

import base64
import datetime
import mimetypes
import re
from pathlib import Path

import markdown as md
from weasyprint import HTML

# Label shown in the top right of the header and used for the file name.
DOC_TITLE = "Investment Sourcing Brief"

# Name shown in the provenance footer. Edit to your own name.
PREPARED_BY = "Maryland Momentum Fund"

# Resolve paths from the package root so the tool runs from any directory.
BASE_DIR = Path(__file__).resolve().parent.parent

# Default file locations inside the package.
TEMPLATE_PATH = BASE_DIR / "templates" / "template.html"
FUND_LOGO_PATH = BASE_DIR / "assets" / "fund_logo.png"

# Section heading keywords that belong in the left sidebar.
SIDEBAR_KEYWORDS = ("quick facts", "traction")

# Labeled lines the system prompt emits at the top of the brief.
FRONT_KEYS = ("SECTOR", "RECOMMENDATION", "SOURCES")


def data_uri(path):
    """
    Read an image file and return it as a base64 data uri.

    Parameters
    path : str
        Path to the image file.

    Returns
    uri : str
        A data uri string, or an empty string if the file is missing.
    """
    image_file = Path(path)
    if not image_file.exists():
        return ""
    mime = mimetypes.guess_type(str(image_file))[0] or "image/png"
    encoded = base64.b64encode(image_file.read_bytes()).decode()
    return f"data:{mime};base64,{encoded}"


def parse_front_matter(markdown_text):
    """
    Pull the labeled front lines off the top of the brief.

    Reads leading lines of the form KEY: value for the keys the system prompt
    emits, and stops at the first blank or unlabeled line.

    Parameters
    markdown_text : str
        The full brief as Markdown, starting with the labeled lines.

    Returns
    front : dict
        Maps each found key to its value.
    body : str
        The brief with the labeled lines removed.
    """
    front = {}
    lines = markdown_text.splitlines()
    index = 0

    # Read consecutive labeled lines until one stops matching a known key.
    for line in lines:
        match = re.match(r"^([A-Z ]+):\s*(.*)$", line)
        if not match or match.group(1).strip() not in FRONT_KEYS:
            break
        front[match.group(1).strip()] = match.group(2).strip()
        index += 1

    body = "\n".join(lines[index:]).lstrip("\n")
    return front, body


def heading_text(section_html):
    """
    Pull the plain text of the h2 at the start of a section.

    Parameters
    section_html : str
        The HTML of one section, starting with an h2 tag.

    Returns
    title : str
        The lowercase heading text, or an empty string.
    """
    match = re.search(r"<h2[^>]*>(.*?)</h2>", section_html, re.S)
    text = match.group(1) if match else ""
    return re.sub(r"<[^>]+>", "", text).strip().lower()


def sort_sections(markdown_text):
    """
    Split the brief into the lead paragraph, sidebar, main, and investor view.

    Parameters
    markdown_text : str
        The brief body as Markdown, with the front lines already removed.

    Returns
    description : str
        HTML for the lead text before the first heading, with the outer
        paragraph tags stripped so it nests cleanly in the template.
    sidebar : str
        HTML for the sidebar boxes.
    main : str
        HTML for the main column boxes.
    investor : str
        HTML for the full width investor view box.
    """
    html_body = md.markdown(markdown_text, extensions=["sane_lists", "tables"])
    pieces = re.split(r"(?=<h2)", html_body)

    # The template already wraps the lead text in a paragraph, so drop the one
    # Markdown adds to avoid invalid nested paragraphs.
    description = pieces[0].strip()
    if description.startswith("<p>") and description.endswith("</p>"):
        description = description[3:-4]

    sidebar, main, investor = [], [], []

    # Route each section to its place based on the heading text.
    for section in pieces[1:]:
        title = heading_text(section)
        if "investor view" in title:
            investor.append(f'<div class="box highlight">{section}</div>')
        elif any(word in title for word in SIDEBAR_KEYWORDS):
            sidebar.append(f'<div class="box">{section}</div>')
        else:
            main.append(f'<div class="box">{section}</div>')

    return description, "".join(sidebar), "".join(main), "".join(investor)


def render_pdf(markdown_text, company_name, out_dir,
               template_path=TEMPLATE_PATH, fund_logo=FUND_LOGO_PATH):
    """
    Fill the template with the brief and write branded HTML and PDF files.

    Parameters
    markdown_text : str
        The brief as Markdown.
    company_name : str
        The company name, shown as the headline.
    out_dir : str
        Folder to write the output files into.
    template_path : str
        Path to the HTML template.
    fund_logo : str
        Path to the fund logo image.

    Returns
    html_path : Path
        Path to the branded HTML file.
    pdf_path : Path
        Path to the branded PDF file.
    """
    template = Path(template_path).read_text(encoding="utf-8")

    # Split the labeled front lines off, then route the remaining sections.
    front, body = parse_front_matter(markdown_text)
    description, sidebar, main, investor = sort_sections(body)

    # Fill every placeholder token in the template.
    filled = (
        template
        .replace("{{FUND_LOGO}}", data_uri(fund_logo))
        .replace("{{DOC_TITLE}}", DOC_TITLE)
        .replace("{{DATE}}", datetime.date.today().strftime("%B %d, %Y"))
        .replace("{{COMPANY}}", company_name)
        .replace("{{SECTOR}}", front.get("SECTOR", "Not disclosed"))
        .replace("{{RECOMMENDATION}}", front.get("RECOMMENDATION", "Not disclosed"))
        .replace("{{SOURCES}}", front.get("SOURCES", "Not disclosed"))
        .replace("{{PREPARED_BY}}", PREPARED_BY)
        .replace("{{DESCRIPTION}}", description)
        .replace("{{SIDEBAR}}", sidebar)
        .replace("{{MAIN}}", main)
        .replace("{{INVESTOR}}", investor)
    )

    safe_name = re.sub(r"[^A-Za-z0-9]+", "_", company_name).strip("_") or "company"
    out_dir = Path(out_dir)
    out_dir.mkdir(exist_ok=True)

    html_path = out_dir / f"{safe_name}_onepager.html"
    pdf_path = out_dir / f"{safe_name}_onepager.pdf"

    html_path.write_text(filled, encoding="utf-8")
    HTML(string=filled, base_url=str(BASE_DIR)).write_pdf(str(pdf_path))
    return html_path, pdf_path