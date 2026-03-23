# File Download Examples

This folder contains examples of downloading files from the internet within ICP canisters using HTTP outcalls.

## Files

| File | Description |
|------|-------------|
| `simple_download.py` | Minimal example - download and print content |
| `word_counter.py` | Full example with state persistence and word counting |

## Quick Start

```bash
# Run once (simple example)
realms run --file examples/file_download/simple_download.py

# Run word counter every 5 minutes
realms run --file examples/file_download/word_counter.py --every 300

# Check task status
realms ps ls
```

## Documentation

See [EXAMPLE_FILE_DOWNLOAD.md](../../docs/EXAMPLE_FILE_DOWNLOAD.md) for detailed documentation.
