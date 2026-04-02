#!/usr/bin/env python3
"""Convert dfx.json to icp.yaml for icp-cli compatibility.

icp-cli requires icp.yaml to identify the project root and define canisters.
This script reads dfx.json and generates an equivalent icp.yaml.
"""

import json
import sys
import os


def convert_dfx_to_icp_yaml(dfx_path="dfx.json", output_path="icp.yaml"):
    """Convert dfx.json canister definitions to icp.yaml format."""
    with open(dfx_path) as f:
        dfx = json.load(f)

    canisters = dfx.get("canisters", {})
    if not canisters:
        # Minimal icp.yaml with no canisters
        with open(output_path, "w") as f:
            f.write("canisters: []\n")
        return

    lines = ["canisters:"]

    for name, config in canisters.items():
        canister_type = config.get("type", "custom")
        build_cmd = config.get("build", "")
        wasm_path = config.get("wasm", "")
        candid_path = config.get("candid", "")
        init_arg = config.get("init_arg", "")
        source_dirs = config.get("source", [])

        lines.append(f"- name: {name}")

        if canister_type == "assets":
            # Asset canister: use pre-built assetstorage WASM + asset sync
            asset_dir = source_dirs[0] if source_dirs else f"src/{name}/dist"
            lines.append("  build:")
            lines.append("    steps:")
            lines.append("    - type: pre-built")
            lines.append("      url: https://github.com/dfinity/sdk/raw/refs/tags/0.30.2/src/distributed/assetstorage.wasm.gz")
            lines.append("  sync:")
            lines.append("    steps:")
            lines.append("    - type: assets")
            lines.append(f"      dir: {asset_dir}")
            if init_arg:
                escaped = init_arg.replace('\\', '\\\\').replace('"', '\\"')
                lines.append(f'  init_args: "{escaped}"')
            continue

        # Non-asset canisters: use build steps
        lines.append("  build:")
        lines.append("    steps:")
        lines.append("    - type: script")
        lines.append("      commands:")

        if build_cmd:
            # Custom canister with a build command (e.g., basilisk backends)
            if candid_path and not candid_path.startswith("http"):
                lines.append(f"      - CANISTER_CANDID_PATH={candid_path} {build_cmd}")
            else:
                lines.append(f"      - {build_cmd}")
            if wasm_path and not wasm_path.startswith("http"):
                lines.append(f"      - cp {wasm_path} $ICP_WASM_OUTPUT_PATH")
        elif wasm_path:
            # Custom canister with pre-built WASM (possibly a URL)
            if wasm_path.startswith("http"):
                lines.append(f"      - curl -fSL -o $ICP_WASM_OUTPUT_PATH {wasm_path}")
            else:
                lines.append(f"      - cp {wasm_path} $ICP_WASM_OUTPUT_PATH")
        else:
            # Fallback: no-op build
            lines.append(f"      - echo no build for {name}")

        # Add init_args if present (icp deploy reads these from icp.yaml)
        if init_arg:
            # YAML quoting: use double quotes and escape internal double quotes
            escaped = init_arg.replace('\\', '\\\\').replace('"', '\\"')
            lines.append(f'  init_args: "{escaped}"')

    with open(output_path, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Generated {output_path} from {dfx_path} ({len(canisters)} canisters)")


if __name__ == "__main__":
    dfx_path = sys.argv[1] if len(sys.argv) > 1 else "dfx.json"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "icp.yaml"
    if not os.path.exists(dfx_path):
        print(f"Error: {dfx_path} not found", file=sys.stderr)
        sys.exit(1)
    convert_dfx_to_icp_yaml(dfx_path, output_path)
