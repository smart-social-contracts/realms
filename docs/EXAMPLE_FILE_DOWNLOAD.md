# Example: File Download from Internet

This example demonstrates how to download files from the internet within an ICP canister using HTTP outcalls.

---

## Overview

ICP canisters can make HTTP requests to external services using the management canister's `http_request` function. This is an **async operation** that requires:

1. Using `yield` to wait for the response
2. Paying cycles for the HTTP request
3. Handling the response with pattern matching

---

## Quick Start

```bash
# Run the simple download example once
realms run --file examples/file_download/simple_download_codex.py

# Run the word counter every 5 minutes
realms run --file examples/file_download/word_counter_codex.py --every 300

# Monitor the task
realms ps ls
realms ps logs <task_id>
```

---

## Simple Example

The minimal code to download a file:

```python
from kybra import ic, Async, CallResult, match
from kybra.canisters.management import management_canister, HttpResponse

def async_task() -> Async[str]:
    """Download a file and return its content."""
    
    http_result: CallResult[HttpResponse] = yield management_canister.http_request(
        {
            "url": "https://example.com",
            "max_response_bytes": 10_000,
            "method": {"get": None},
            "headers": [],
            "body": None,
            "transform": None,
        }
    ).with_cycles(100_000_000)
    
    return match(
        http_result,
        {
            "Ok": lambda r: r["body"].decode("utf-8"),
            "Err": lambda e: f"Error: {e}",
        }
    )
```

---

## Full Example: Word Counter

The [word_counter_codex.py](../examples/file_download/word_counter_codex.py) demonstrates:

### 1. HTTP Outcall with Headers

```python
http_result: CallResult[HttpResponse] = yield management_canister.http_request(
    {
        "url": URL,
        "max_response_bytes": 100_000,  # 100KB limit
        "method": {"get": None},
        "headers": [
            {"name": "User-Agent", "value": "Realms-WordCounter/1.0"}
        ],
        "body": None,
        "transform": None,
    }
).with_cycles(100_000_000)
```

### 2. State Persistence with TaskEntity

```python
class WordCountState(TaskEntity):
    __alias__ = "key"
    key = String(max_length=256)
    value = String(max_length=5000)

# Get or create state
state = WordCountState["last_result"]
if not state:
    state = WordCountState(key="last_result", value="{}")

# Update state
state.value = json.dumps({"word_count": 1234, "timestamp": int(ic.time())})
```

### 3. Response Handling

```python
def handle_response(response: HttpResponse) -> str:
    content = response["body"].decode("utf-8")
    word_count = len(content.split())
    return json.dumps({"word_count": word_count})

def handle_error(err: str) -> str:
    return json.dumps({"error": err})

return match(http_result, {"Ok": handle_response, "Err": handle_error})
```

---

## HTTP Request Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `url` | string | Target URL (must be HTTPS for mainnet) |
| `max_response_bytes` | int | Maximum response size (costs more cycles for larger) |
| `method` | variant | `{"get": None}`, `{"post": None}`, `{"head": None}` |
| `headers` | list | List of `{"name": "...", "value": "..."}` objects |
| `body` | bytes/None | Request body for POST requests |
| `transform` | object/None | Optional transform function for consensus |

---

## Cycles Cost

HTTP outcalls require cycles. The cost depends on:

- Request size
- Response size (max_response_bytes)
- Number of subnet nodes

**Recommended**: Start with 100M cycles (`.with_cycles(100_000_000)`)

```python
# For small responses
.with_cycles(100_000_000)    # 100M cycles

# For larger responses (up to 1MB)
.with_cycles(500_000_000)    # 500M cycles

# For very large responses
.with_cycles(15_000_000_000) # 15B cycles
```

---

## Important Notes

### HTTPS Required on Mainnet

On the IC mainnet, only HTTPS URLs are allowed. HTTP works only on local development.

### Response Size Limits

- Maximum response: 2MB
- Set `max_response_bytes` appropriately to control costs

### Async Requirement

HTTP outcalls are **always async**. You must:
1. Define an `async_task()` function
2. Use `yield` to await the response
3. The task will be scheduled via TaskManager

### Transform Function (Optional)

For consensus, all replicas must agree on the response. Use a transform function to normalize responses:

```python
"transform": {
    "function": (ic.id(), "http_transform"),
    "context": bytes(),
}
```

---

## Scheduling as Recurring Task

```bash
# Run every 60 seconds
realms run --file examples/file_download/word_counter_codex.py --every 60

# Run every 5 minutes, starting after 10 seconds
realms run --file examples/file_download/word_counter_codex.py --every 300 --after 10

# List all scheduled tasks
realms ps ls

# View logs
realms ps logs <task_id>

# Stop task
realms ps kill <schedule_id>
```

---

## Related Documentation

- [Scheduled Tasks](./DEPLOYMENT_GUIDE.md#scheduled-tasks)
- [Task Entity Persistence](./TASK_ENTITY.md)
- [ICP HTTP Outcalls](https://internetcomputer.org/docs/current/developer-docs/smart-contracts/advanced-features/https-outcalls/)

---

## Files

| File | Description |
|------|-------------|
| [`examples/file_download/simple_download_codex.py`](../examples/file_download/simple_download_codex.py) | Minimal download example |
| [`examples/file_download/word_counter_codex.py`](../examples/file_download/word_counter_codex.py) | Full example with state persistence |
