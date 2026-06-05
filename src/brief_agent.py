"""
Brief agent.

Runs Claude with live web search to write the sourcing brief. It packs the
labeled notes and any uploaded PDF documents into one user message, sends it
with the system prompt that defines the output, and returns the finished brief
as Markdown.

Required environment variable:
    ANTHROPIC_API_KEY : an Anthropic API key
"""

import base64
from pathlib import Path

from anthropic import Anthropic

# Model used for the brief. Swap to claude-sonnet-4-6 for a cheaper run.
MODEL = "claude-opus-4-8"

# Web search tool definition. max_uses caps searches per brief to control cost.
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 8}

# Upper bound on the length of the model response in tokens.
MAX_TOKENS = 8000


def encode_pdf(path):
    """
    Read a PDF file and return it as a base64 string.

    Parameters
    path : Path
        Path to the PDF file.

    Returns
    encoded : str
        The file contents as a base64 encoded string.
    """
    return base64.standard_b64encode(Path(path).read_bytes()).decode("utf-8")


def build_brief(company_name, notes_text, pdf_paths, system_prompt):
    """
    Write the sourcing brief with Claude and web search.

    Sends the labeled notes as text and each PDF as a native document block so
    Claude reads them at full fidelity. The model then researches the company
    online and returns the finished brief as Markdown.

    Parameters
    company_name : str
        The company to research.
    notes_text : str
        All text and Markdown inputs concatenated, each labeled by filename.
    pdf_paths : list
        Paths to any PDF files in the inputs folder.
    system_prompt : str
        The instruction template that defines the output format and rules.

    Returns
    brief : str
        The one page brief as Markdown.
    """
    client = Anthropic()

    # Build the content list. Text notes come first as a single block, then
    # each PDF follows as a native document block so the model reads it whole.
    content = [
        {
            "type": "text",
            "text": (
                f"Build a one page sourcing brief for: {company_name}\n\n"
                f"== NOTES ==\n{notes_text or 'No notes provided.'}\n\n"
                "Research the company online to verify claims and fill gaps, "
                "then output the brief in Markdown following the template and "
                "rules exactly."
            ),
        }
    ]

    # Append one document block per PDF so the model sees the full file.
    for pdf_path in pdf_paths:
        content.append(
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": encode_pdf(pdf_path),
                },
                "title": Path(pdf_path).name,
            }
        )

    # Server side web search can pause a long turn. When it does, send the
    # partial response back and let Claude keep going until the turn ends.
    messages = [{"role": "user", "content": content}]
    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            tools=[WEB_SEARCH_TOOL],
            messages=messages,
        )
        if response.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": response.content})
            continue
        break

    # Keep only the text blocks. Search result blocks are not part of the brief.
    return "".join(
        block.text for block in response.content
        if getattr(block, "type", None) == "text"
    ).strip()