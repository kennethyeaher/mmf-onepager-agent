"""
HubSpot client.

Pulls a company record and its associated notes from HubSpot through the CRM
API. Going through the REST API means notes are readable even when HubSpot's
Sensitive Data setting would hide them from the MCP server.

This module is dormant in the current pipeline. The tool reads from a per
company inputs folder instead, so main.py does not import it. It stays in the
repo to be re enabled behind a flag once the HubSpot keys are approved.

Required environment variable:
    HUBSPOT_TOKEN : a HubSpot private app token with CRM read scopes
"""

import html
import os
import re

import requests

# Base URL for all HubSpot CRM requests.
HUBSPOT_BASE = "https://api.hubapi.com"

# How long to wait on any single HubSpot request before giving up, in seconds.
REQUEST_TIMEOUT = 30

# HubSpot batch read accepts at most 100 ids per call.
BATCH_LIMIT = 100


def hubspot_headers():
    """
    Build the auth headers for HubSpot requests.

    Parameters
    none

    Returns
    headers : dict
        Authorization and content type headers.

    Raises
    RuntimeError
        If the HUBSPOT_TOKEN environment variable is not set.
    """
    token = os.environ.get("HUBSPOT_TOKEN")
    if not token:
        raise RuntimeError("set the HUBSPOT_TOKEN environment variable")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def strip_html(raw_body):
    """
    Turn a HubSpot note body into clean plain text.

    HubSpot stores note bodies as HTML, so we convert breaks and paragraphs to
    line breaks and drop the remaining tags.

    Parameters
    raw_body : str
        The raw note body as returned by HubSpot.

    Returns
    text : str
        The note body as plain text.
    """
    raw_body = re.sub(r"<br\s*/?>", "\n", raw_body, flags=re.I)
    raw_body = re.sub(r"</p\s*>", "\n", raw_body, flags=re.I)
    raw_body = re.sub(r"<[^>]+>", "", raw_body)
    return html.unescape(raw_body).strip()


def find_company(name):
    """
    Search HubSpot companies by name.

    Parameters
    name : str
        The company name to search for.

    Returns
    company : dict or None
        The top matching company record, or None if there is no match.
    """
    url = f"{HUBSPOT_BASE}/crm/v3/objects/companies/search"
    payload = {
        "filterGroups": [
            {"filters": [{"propertyName": "name", "operator": "CONTAINS_TOKEN", "value": name}]}
        ],
        "properties": ["name", "domain", "website"],
        "limit": 5,
    }
    response = requests.post(url, headers=hubspot_headers(), json=payload, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    results = response.json().get("results", [])
    return results[0] if results else None


def get_note_ids(company_id):
    """
    Find the notes associated with a company, following pagination.

    Parameters
    company_id : str
        The HubSpot id of the company.

    Returns
    note_ids : list
        The ids of all notes associated with the company.
    """
    url = f"{HUBSPOT_BASE}/crm/v4/objects/companies/{company_id}/associations/notes"
    note_ids = []
    params = {"limit": 500}

    # Walk every page of associations so large note sets are not truncated.
    while True:
        response = requests.get(url, headers=hubspot_headers(), params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        body = response.json()
        note_ids.extend(row["toObjectId"] for row in body.get("results", []))
        after = body.get("paging", {}).get("next", {}).get("after")
        if not after:
            return note_ids
        params["after"] = after


def read_notes(note_ids):
    """
    Read note bodies for a list of note ids, in chunks.

    Parameters
    note_ids : list
        The note ids to read.

    Returns
    notes : list
        Note dicts, each with a timestamp and a plain text body, sorted oldest
        to newest. Empty notes are dropped.
    """
    notes = []
    url = f"{HUBSPOT_BASE}/crm/v3/objects/notes/batch/read"

    # Read in chunks because the batch endpoint caps the ids per call.
    for start in range(0, len(note_ids), BATCH_LIMIT):
        chunk = note_ids[start:start + BATCH_LIMIT]
        payload = {
            "properties": ["hs_note_body", "hs_timestamp"],
            "inputs": [{"id": str(note_id)} for note_id in chunk],
        }
        response = requests.post(url, headers=hubspot_headers(), json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        # Convert each HubSpot note into a simple dict of timestamp and clean text.
        for obj in response.json().get("results", []):
            body = strip_html(obj["properties"].get("hs_note_body") or "")
            timestamp = obj["properties"].get("hs_timestamp", "")
            if body:
                notes.append({"timestamp": timestamp, "body": body})

    notes.sort(key=lambda note: note["timestamp"])
    return notes


def fetch_company_notes(company_name):
    """
    Look up a company and pull all of its notes.

    Parameters
    company_name : str
        The company name to search for.

    Returns
    company : dict or None
        The matched company record, or None if there is no match.
    notes : list
        The company's notes, or an empty list.
    """
    company = find_company(company_name)
    if not company:
        return None, []
    notes = read_notes(get_note_ids(company["id"]))
    return company, notes