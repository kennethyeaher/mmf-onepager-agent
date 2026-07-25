"""
Library.

Keeps a small index of every generated brief so the web app can show a brief
library and a recent list without guessing details from file paths. The index
is a single json file inside the output folder. Each entry records the display
name, the sector, the recorded recommendation, the pdf file name, and the save
time.

Briefs generated before this module existed still appear. The reader merges
the index with a scan of the output folder, so a pdf with no index entry shows
up with a name derived from its file name and a blank sector.
"""

import datetime
import json
from pathlib import Path

# File name of the index inside the output folder.
INDEX_NAME = "index.json"


def load_index(out_dir):
    """
    Read the index file from the output folder.

    Parameters
    out_dir : Path
        The output folder.

    Returns
    index : dict
        Maps each pdf file name to its entry, or an empty dict when the index
        file is missing or unreadable.
    """
    index_path = Path(out_dir) / INDEX_NAME
    if not index_path.exists():
        return {}

    # A damaged index should never break the app, so fall back to empty.
    try:
        return json.loads(index_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_index(out_dir, index):
    """
    Write the index file into the output folder.

    Parameters
    out_dir : Path
        The output folder.
    index : dict
        Maps each pdf file name to its entry.

    Returns
    none
    """
    out_path = Path(out_dir)
    out_path.mkdir(exist_ok=True)
    index_path = out_path / INDEX_NAME
    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")


def record_brief(out_dir, pdf_path, company_name, sector, recommendation):
    """
    Add or update the index entry for a generated brief.

    Called after a successful render. Reruns for the same company overwrite
    the earlier entry, so the library always shows the latest run.

    Parameters
    out_dir : Path
        The output folder.
    pdf_path : Path
        Path to the rendered pdf, used for the entry key.
    company_name : str
        The display name typed into the form.
    sector : str
        The sector label shown on the brief.
    recommendation : str
        The recorded team decision, or an empty string.

    Returns
    none
    """
    index = load_index(out_dir)

    # Key the entry by pdf file name so the reader can join it to the file.
    index[Path(pdf_path).name] = {
        "name": company_name,
        "sector": sector,
        "recommendation": recommendation,
        "saved": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    save_index(out_dir, index)


def derive_name(pdf_name):
    """
    Build a readable display name from a pdf file name.

    Used for briefs generated before the index existed. Strips the onepager
    suffix and turns underscores into spaces.

    Parameters
    pdf_name : str
        The pdf file name, for example Activate_onepager.pdf.

    Returns
    name : str
        A readable name, for example Activate.
    """
    stem = Path(pdf_name).stem
    if stem.endswith("_onepager"):
        stem = stem[: -len("_onepager")]
    return stem.replace("_", " ").strip() or pdf_name


def relative_time(saved):
    """
    Turn a save time into a short phrase like 2 days ago.

    Parameters
    saved : datetime.datetime
        The save time.

    Returns
    phrase : str
        A short relative phrase.
    """
    delta = datetime.datetime.now() - saved
    seconds = max(int(delta.total_seconds()), 0)

    # Walk from the smallest unit up and stop at the first fitting one.
    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} minute ago" if minutes == 1 else f"{minutes} minutes ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour ago" if hours == 1 else f"{hours} hours ago"
    days = hours // 24
    if days < 7:
        return f"{days} day ago" if days == 1 else f"{days} days ago"
    weeks = days // 7
    return f"{weeks} week ago" if weeks == 1 else f"{weeks} weeks ago"


def list_briefs(out_dir):
    """
    List every saved brief, newest first.

    Merges the index with a scan of the output folder. A pdf with an index
    entry uses its recorded details. A pdf without one gets a derived name,
    a blank sector, and its file modified time as the save time.

    Parameters
    out_dir : Path
        The output folder.

    Returns
    briefs : list
        One dict per brief with name, sector, recommendation, file, saved,
        and ago keys, sorted newest first.
    """
    out_path = Path(out_dir)
    if not out_path.exists():
        return []

    index = load_index(out_dir)
    briefs = []

    # Walk the real files so deleted briefs never linger in the list.
    for pdf in out_path.glob("*.pdf"):
        entry = index.get(pdf.name)
        if entry:
            saved = datetime.datetime.fromisoformat(entry["saved"])
            name = entry.get("name") or derive_name(pdf.name)
            sector = entry.get("sector", "")
            recommendation = entry.get("recommendation", "")
        else:
            saved = datetime.datetime.fromtimestamp(pdf.stat().st_mtime)
            name = derive_name(pdf.name)
            sector = ""
            recommendation = ""

        briefs.append({
            "name": name,
            "sector": sector,
            "recommendation": recommendation,
            "file": pdf.name,
            "saved": saved.isoformat(timespec="seconds"),
            "ago": relative_time(saved),
        })

    # Newest first so the recent list is just the top slice.
    briefs.sort(key=lambda brief: brief["saved"], reverse=True)
    return briefs