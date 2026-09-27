"""Bounded Europe PMC search and record retrieval for PubCrawler.

Only the fixed Europe PMC HTTPS API endpoint is contacted. No arbitrary URLs,
full-text downloads, or network access are exposed to the agent.
"""

import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from agents.decorators import tool


API = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
MAX_RESPONSE_BYTES = 2_000_000
MAX_QUERY_CHARS = 500


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


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
