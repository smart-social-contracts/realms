"""
Simple File Download Codex - Minimal example of HTTP outcalls.

This is a stripped-down version showing only the essential parts
of making an HTTP request from an ICP canister.

Usage:
    realms run --file examples/file_download/simple_download.py
"""

from _cdk import ic, Async, CallResult, match
from _cdk import management_canister, HttpResponse
import json


def async_task() -> Async[str]:
    """Download a file and print its first 500 characters."""
    
    url = "https://example.com"
    
    ic.print(f"📥 Downloading: {url}")
    
    # HTTP outcall - must use yield (async)
    http_result: CallResult[HttpResponse] = yield management_canister.http_request(
        {
            "url": url,
            "max_response_bytes": 10_000,
            "method": {"get": None},
            "headers": [],
            "body": None,
            "transform": None,
        }
    ).with_cycles(100_000_000)
    
    # Handle result using pattern matching
    return match(
        http_result,
        {
            "Ok": lambda r: f"✅ Downloaded {len(r['body'])} bytes:\n{r['body'].decode('utf-8')[:500]}",
            "Err": lambda e: f"❌ Error: {e}",
        }
    )
