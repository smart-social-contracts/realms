"""
HTTP utility functions for making outcalls from canisters.
This module is safe to import from extensions as it has no lifecycle decorators.
"""

from typing import Tuple

from kybra import Async, CallResult, ic, match, update
from kybra.canisters.management import HttpResponse, management_canister

# Cache for downloaded content
downloaded_content: dict = {}


@update
def download_file_from_url(url: str) -> Async[Tuple[bool, str]]:
    """
    Download file from a URL.

    Returns:
        Tuple of (success: bool, result: str)
        - If success=True, result contains the downloaded file content
        - If success=False, result contains the error message
    """

    try:
        ic.print(f"Downloading code from URL: {url}")

        # Make HTTP request to download the code
        http_result: CallResult[HttpResponse] = yield management_canister.http_request(
            {
                "url": url,
                "max_response_bytes": 1024 * 1024,  # 1MB limit for security
                "method": {"get": None},
                "headers": [
                    {"name": "User-Agent", "value": "Realms-Codex-Downloader/1.0"}
                ],
                "body": None,
                "transform": {
                    "function": (ic.id(), "http_transform"),
                    "context": bytes(),
                },
            }
        ).with_cycles(15_000_000_000)

        def handle_response(response: HttpResponse) -> Tuple[bool, str]:
            try:
                # Decode the response body
                code_content = response["body"].decode("utf-8")
                ic.print(f"Successfully downloaded {len(code_content)} bytes")

                downloaded_content[url] = code_content
                return True, code_content

            except UnicodeDecodeError as e:
                error_msg = f"Failed to decode response as UTF-8: {str(e)}"
                ic.print(error_msg)
                return False, error_msg
            except Exception as e:
                error_msg = f"Error processing response: {str(e)}"
                ic.print(error_msg)
                return False, error_msg

        def handle_error(err: str) -> Tuple[bool, str]:
            error_msg = f"HTTP request failed: {err}"
            ic.print(error_msg)
            return False, error_msg

        return match(http_result, {"Ok": handle_response, "Err": handle_error})

    except Exception as e:
        error_msg = f"Unexpected error downloading code: {str(e)}"
        ic.print(error_msg)
        return False, error_msg
