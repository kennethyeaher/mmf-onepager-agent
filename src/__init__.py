"""
MMF one pager agent source package.

Three modules carry the pipeline. hubspot_client pulls a company and its notes
from HubSpot, brief_agent runs Claude with web search to write the brief, and
renderer turns the brief into the branded PDF.
"""