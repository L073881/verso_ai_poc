# prompts.py

CREATE_PROMPT = """
You are a Documentation Specialist. Using the repository template profile and Jira ticket information, create a complete Markdown design document.

Template Profile:
{template_profile}

Jira Ticket:
{ticket_key}
{ticket_summary}
{ticket_description}

Constraints:
- Follow the template headings exactly.
- Include sections: Overview, Architecture, APIs, Data Model, Sequence Flow, Deployment, Ownership, Change Log.
- Use markdown fenced code blocks for examples.
- If missing info, insert [TODO: ...] placeholders.
- Output only the complete markdown document.
"""

UPDATE_PROMPT = """
You are a Documentation Specialist. Update the existing document sections below according to the Jira ticket.

Existing Document Sections:
{existing_sections}

Jira Ticket:
{ticket_key}
{ticket_summary}
{ticket_description}

Constraints:
- Preserve headings and formatting.
- Modify only the relevant sections.
- Add a Change Log entry at the top referencing the ticket.
- Output the entire updated markdown document only.
"""

TEMPLATE_EXTRACT_PROMPT = """
You are a tool that extracts a document style profile from example Markdown docs.
Return strict JSON with keys:
- headings: ordered list of headings
- code_block_style: "fenced" or "indented"
- list_style: "dash" or "number"
- diagram_types: list (e.g. ["mermaid"])
- footer_sections: list

Documents:
{examples}
"""
