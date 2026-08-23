"""Tests for codex publish namespace routing."""

import json
import os
import tempfile
from unittest.mock import patch

from realms.cli.commands.extension import publish_codex_command


def test_unified_codex_publish_uses_codex_namespace_prefix():
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "backend"))
        with open(os.path.join(tmp, "manifest.json"), "w") as fh:
            json.dump(
                {
                    "id": "syntropia",
                    "version": "1.0.0",
                    "kind": "codex",
                },
                fh,
            )
        with open(os.path.join(tmp, "backend", "entry.py"), "w") as fh:
            fh.write("# codex backend\n")

        with patch(
            "realms.cli.commands.extension.publish_extension_command"
        ) as mock_publish:
            publish_codex_command(
                registry="file-reg",
                source_dir=tmp,
                network="local",
            )

        mock_publish.assert_called_once()
        assert mock_publish.call_args.kwargs["namespace_prefix"] == "codex"
