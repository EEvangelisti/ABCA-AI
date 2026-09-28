"""Bounded literature tools for PubCrawler.

Provides:
- Europe PMC metadata and abstract search;
- retrieval of individual Europe PMC records;
- text extraction from local PDF files supplied in the input-data directory.

Only the fixed Europe PMC HTTPS API endpoint is contacted. No arbitrary URLs
or full-text downloads are exposed to the agent. Local PDF access is restricted
to the configured input-data directory.
"""

import json
import re
import source.config as config
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from agents.decorators import tool

from pathlib import Path
from pypdf import PdfReader


API = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
MAX_RESPONSE_BYTES = 2_000_000
MAX_QUERY_CHARS = 500

class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None

MAX_PDF_PAGES = 200
MAX_PDF_TEXT_CHARS = 500_000


@tool
def extract_pdf_text(path: str) -> str:
    """Extract text from a local PDF available to the agent.

    Use this tool for PDF documents already present in the input data,
    such as supplied publications, reports, or supplementary material.

    This tool does not download PDFs or access arbitrary URLs.
    Scanned/image-only PDFs may return little or no text.
    """
    try:
      PDF_ROOT = Path(config.INPUT_DATA_DIR).resolve()
      pdf_path = (PDF_ROOT / path).resolve()

      if not pdf_path.is_relative_to(PDF_ROOT):
          return "Access denied: PDF must be inside the input-data directory."

        if pdf_path.suffix.lower() != ".pdf":
            return "Invalid file: expected a PDF."

        if not pdf_path.is_file():
            return f"PDF not found: {path}"

        reader = PdfReader(str(pdf_path))

        if len(reader.pages) > MAX_PDF_PAGES:
            return (
                f"PDF has {len(reader.pages)} pages; "
                f"maximum allowed is {MAX_PDF_PAGES}."
            )

        chunks = []
        total_chars = 0

        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""

            remaining = MAX_PDF_TEXT_CHARS - total_chars
            if remaining <= 0:
                break

            text = text[:remaining]

            chunks.append(
                f"\n--- PAGE {page_number} ---\n{text}"
            )

            total_chars += len(text)

        extracted = "".join(chunks).strip()

        if not extracted:
            return (
                "No extractable text found in PDF. "
                "The document may be scanned or image-only."
            )

        if total_chars >= MAX_PDF_TEXT_CHARS:
            extracted += (
                f"\n\n[TEXT TRUNCATED AT "
                f"{MAX_PDF_TEXT_CHARS:,} CHARACTERS]"
            )

        return extracted

    except Exception as exc:
        return f"PDF extraction failed: {exc}"




def _search(query: str, limit: int) -> dict:
    params = urlencode({
        "query": query, "format": "json", "resultType": "core",
        "pageSize": limit,
    })
    request = Request(
        f"{API}?{params}",
        headers={"Accept": "application/json", "User-Agent": "ABCA-AI/1.0 research"},
    )
    with build_opener(_NoRedirect).open(request, timeout=15) as response:
        payload = response.read(MAX_RESPONSE_BYTES + 1)
    if len(payload) > MAX_RESPONSE_BYTES:
        raise ValueError("Europe PMC response exceeds the size limit")
    return json.loads(payload)


def _record(item: dict) -> dict:
    return {
        "title": item.get("title"),
        "authors": item.get("authorString"),
        "journal": item.get("journalTitle"),
        "year": item.get("pubYear"),
        "doi": item.get("doi"),
        "pmid": item.get("pmid"),
        "pmcid": item.get("pmcid"),
        "source": item.get("source"),
        "source_id": item.get("id"),
        "publication_type": item.get("pubTypeList"),
        "is_open_access": item.get("isOpenAccess"),
        "abstract": (item.get("abstractText") or "")[:16_000],
        "record_url": (
            f"https://europepmc.org/article/{item['source']}/{item['id']}"
            if item.get("source") and item.get("id") else None
        ),
    }


@tool
def search_literature(query: str, limit: int = 10) -> str:
    """Search Europe PMC article metadata and abstracts; return up to 20 records.

    Use a focused scientific query. Results are indexed records, not evidence
    that the agent has read the full paper.
    """
    if not isinstance(query, str) or not query.strip() or len(query) > MAX_QUERY_CHARS:
        return "Invalid query: supply 1-500 characters."
    limit = min(max(int(limit), 1), 20)
    try:
        result = _search(query, limit)
        records = result.get("resultList", {}).get("result", [])
        return json.dumps({
            "query": query, "hit_count": result.get("hitCount"),
            "records": [_record(item) for item in records[:limit]],
        }, ensure_ascii=False)
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        return f"Europe PMC search failed: {exc}"


@tool
def get_literature_record(identifier: str) -> str:
    """Retrieve Europe PMC metadata and abstract by DOI, PMID or PMCID.

    Full text is not retrieved. Cite the returned DOI or record URL and say
    explicitly when the abstract is unavailable.
    """
    identifier = identifier.strip()
    if re.fullmatch(r"PMC\d+", identifier, re.I):
        query = f"EXT_ID:{identifier.upper()} AND SRC:PMC"
    elif re.fullmatch(r"\d{1,12}", identifier):
        query = f"EXT_ID:{identifier} AND SRC:MED"
    elif re.fullmatch(r"10\.\d{4,9}/[^\s\"'<>]{1,180}", identifier, re.I):
        query = f'DOI:"{identifier}"'
    else:
        return "Invalid identifier: expected a DOI, PMID or PMCID."
    try:
        items = _search(query, 2).get("resultList", {}).get("result", [])
        return json.dumps({"identifier": identifier,
                           "records": [_record(item) for item in items]},
                          ensure_ascii=False)
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        return f"Europe PMC retrieval failed: {exc}"
