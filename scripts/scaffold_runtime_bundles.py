#!/usr/bin/env python3
"""
scaffold_runtime_bundles.py — generate a per-extension `frontend-rt/` directory
for every extension in `realms-extensions/extensions/` that does not yet have
one.

Background (Issue #168 / Layer 2)
---------------------------------
With the Layered Realm architecture, every extension UI must ship as a single
self-contained ESM bundle that:

  * exports `default mountExt(target, props) => { unmount() }`
  * is uploaded to `file_registry` under `ext/<id>/<version>/frontend/dist/index.js`
  * is dynamic-imported by `realm_frontend`'s extension-loader at runtime
  * brings its own Svelte 5 runtime, CSS, and i18n (no host stores!)

`realms-extensions/extensions/member_dashboard/frontend-rt/` is the canonical
hand-written reference. This script clones that template into every other
extension so the build/publish pipeline can iterate over all 20 extensions
uniformly.

What gets generated for `<ext>`:

    realms-extensions/extensions/<ext>/frontend-rt/
        package.json         — name=<ext>-frontend-rt, version=<manifest.version>
        tsconfig.json        — copied verbatim from template
        vite.config.ts       — entry=src/index.ts, formats=['es'], inlineDynamicImports
        src/index.ts         — Svelte 5 mount(target, props) => { unmount() }
        src/Placeholder.svelte
                             — minimal "<ext> (runtime-loaded) v{version}" card
                               that proves the dynamic-import path works and
                               exposes the host-injected `backend`/`principal`
                               so the operator can then progressively port the
                               extension's real UI on top of this scaffold.

The script is idempotent: by default it skips extensions whose `frontend-rt/`
directory already exists. Pass `--force` to overwrite, or `--only <id>` to
target a single extension. `_shared/` is skipped automatically.

Usage:
    python scripts/scaffold_runtime_bundles.py
    python scripts/scaffold_runtime_bundles.py --extensions-repo ../realms-extensions
    python scripts/scaffold_runtime_bundles.py --only voting --force
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Iterable, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXTENSIONS_REPO = REPO_ROOT.parent / "realms-extensions"

# Extensions to never scaffold (they are not real extensions).
SKIP_EXTENSION_IDS = {"_shared"}

# Extensions whose frontend-rt directory was hand-written and must NEVER be
# overwritten by this script even with --force. (These are the canonical
# templates / proof-of-concept builds.)
PROTECTED_EXTENSION_IDS = {"member_dashboard", "test_bench"}


# ---------------------------------------------------------------------------
# File templates
# ---------------------------------------------------------------------------

PACKAGE_JSON_TMPL = """{{
  "name": "{ext_id}-frontend-rt",
  "version": "{version}",
  "private": true,
  "description": "Runtime-loadable ESM bundle for the {ext_id} extension UI (Issue #168 Layer 2)",
  "type": "module",
  "scripts": {{
    "build": "vite build"
  }},
  "devDependencies": {{
    "@sveltejs/vite-plugin-svelte": "^5.0.0",
    "svelte": "^5.19.0",
    "typescript": "^5.4.0",
    "vite": "^6.0.0"
  }}
}}
"""

TSCONFIG_JSON = """{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "isolatedModules": true,
    "verbatimModuleSyntax": true,
    "allowSyntheticDefaultImports": true,
    "resolveJsonModule": true,
    "types": ["svelte"]
  },
  "include": ["src/**/*", "vite.config.ts"]
}
"""

VITE_CONFIG_TMPL = """import {{ defineConfig }} from 'vite';
import {{ svelte }} from '@sveltejs/vite-plugin-svelte';
import {{ resolve }} from 'node:path';

/**
 * Per-extension build producing a single self-contained ESM bundle for the
 * {ext_id} frontend. Uploaded to file_registry under
 *   ext/{ext_id}/<version>/frontend/dist/index.js
 * and dynamic-imported at runtime by realm_frontend's extension-loader.
 *
 * Output requirements (Issue #168):
 *   - One file: dist/index.js
 *   - ESM with default export `mount(target, props) => {{ unmount() }}`
 *   - All deps inlined (Svelte runtime, no externals)
 *   - CSS inlined into the JS so there is no separate stylesheet to load
 */
export default defineConfig({{
\tplugins: [svelte({{ emitCss: false }})],
\tbuild: {{
\t\tlib: {{
\t\t\tentry: resolve(__dirname, 'src/index.ts'),
\t\t\tname: '{lib_name}',
\t\t\tformats: ['es'],
\t\t\tfileName: () => 'index.js',
\t\t}},
\t\trollupOptions: {{
\t\t\toutput: {{
\t\t\t\tinlineDynamicImports: true,
\t\t\t}},
\t\t}},
\t\tcssCodeSplit: false,
\t\tminify: 'esbuild',
\t\tsourcemap: false,
\t\ttarget: 'es2020',
\t\temptyOutDir: true,
\t}},
}});
"""

INDEX_TS_TMPL = """import { mount, unmount } from 'svelte';
import Placeholder from './Placeholder.svelte';

/**
 * Entry point conforming to the runtime-extension contract used by
 * realm_frontend's extension-loader (src/lib/extension-loader.ts).
 *
 *   default export: mount(target, props) => { unmount() }
 *
 * Host injects an authenticated `backend` actor plus the current
 * user's `principal`. Bundles MUST NOT reach into host-specific
 * stores; everything they need flows through `props`.
 */
export interface RuntimeMountProps {
\tbackend: any;
\textensionId: string;
\tversion: string;
\tprincipal?: string;
\tisAuthenticated?: boolean;
}

export default function mountExt(target: HTMLElement, props: RuntimeMountProps) {
\tconst component = mount(Placeholder, { target, props });
\treturn {
\t\tunmount() {
\t\t\ttry {
\t\t\t\tunmount(component);
\t\t\t} catch {
\t\t\t\t/* already torn down */
\t\t\t}
\t\t},
\t};
}
"""

PLACEHOLDER_SVELTE_TMPL = """<script lang=\"ts\">
\tlet {
\t\tbackend,
\t\textensionId,
\t\tversion,
\t\tprincipal = '',
\t\tisAuthenticated = false,
\t} = $props<{
\t\tbackend: any;
\t\textensionId: string;
\t\tversion: string;
\t\tprincipal?: string;
\t\tisAuthenticated?: boolean;
\t}>();

\tlet pingResult = $state<string | null>(null);
\tlet pingError = $state<string | null>(null);
\tlet pinging = $state(false);

\tasync function ping() {
\t\tpinging = true;
\t\tpingError = null;
\t\tpingResult = null;
\t\ttry {
\t\t\tconst r = await backend.extension_sync_call({
\t\t\t\textension_name: extensionId,
\t\t\t\tfunction_name: 'health',
\t\t\t\targs: '{}',
\t\t\t});
\t\t\tpingResult = JSON.stringify(r, null, 2);
\t\t} catch (e: any) {
\t\t\tpingError = e?.message ?? String(e);
\t\t} finally {
\t\t\tpinging = false;
\t\t}
\t}

\tfunction shortPrincipal(p: string): string {
\t\tif (!p) return '';
\t\tif (p.length <= 14) return p;
\t\treturn p.slice(0, 6) + '…' + p.slice(-4);
\t}
</script>

<div class=\"rt-root\">
\t<header class=\"hero\">
\t\t<span class=\"badge\">v{version}</span>
\t\t<h1>{extensionId} <small>(runtime-loaded)</small></h1>
\t\t<p class=\"sub\">
\t\t\tThis bundle was fetched from <code>file_registry</code> at runtime —
\t\t\tno bundled extension code is shipped in the host realm WASM.
\t\t</p>
\t</header>

\t<section class=\"card\">
\t\t<header class=\"card-head\">
\t\t\t<h2>Host context</h2>
\t\t</header>
\t\t<dl class=\"kv\">
\t\t\t<dt>Authenticated</dt>
\t\t\t<dd>{isAuthenticated ? 'yes' : 'no'}</dd>
\t\t\t<dt>Principal</dt>
\t\t\t<dd class=\"mono\">{shortPrincipal(principal) || '(anonymous)'}</dd>
\t\t\t<dt>Bundle</dt>
\t\t\t<dd class=\"mono\">ext/{extensionId}/{version}/frontend/dist/index.js</dd>
\t\t</dl>
\t</section>

\t<section class=\"card\">
\t\t<header class=\"card-head\">
\t\t\t<h2>Backend smoke test</h2>
\t\t</header>
\t\t<p class=\"sub\">
\t\t\tCalls <code>{`backend.extension_sync_call({ extension_name: '${extensionId}', function_name: 'health', args: '{}' })`}</code>.
\t\t\tIf this extension does not implement <code>health</code>, expect a
\t\t\t<code>function_not_found</code> response — that still proves the call
\t\t\treached the runtime-installed extension.
\t\t</p>
\t\t<button class=\"btn\" disabled={pinging} onclick={ping}>
\t\t\t{pinging ? 'Pinging…' : 'Run health()'}
\t\t</button>
\t\t{#if pingError}
\t\t\t<pre class=\"out err\">{pingError}</pre>
\t\t{/if}
\t\t{#if pingResult}
\t\t\t<pre class=\"out\">{pingResult}</pre>
\t\t{/if}
\t</section>

\t<footer class=\"rt-foot\">
\t\tScaffolded by <code>scripts/scaffold_runtime_bundles.py</code> — replace
\t\t<code>src/Placeholder.svelte</code> with the real UI and re-build.
\t</footer>
</div>

<style>
\t.rt-root {
\t\tfont-family:
\t\t\tsystem-ui, -apple-system, Segoe UI, Roboto, sans-serif;
\t\tcolor: #0f172a;
\t\tmax-width: 960px;
\t\tdisplay: flex;
\t\tflex-direction: column;
\t\tgap: 18px;
\t}
\t.hero {
\t\tborder: 2px solid #3b82f6;
\t\tborder-radius: 12px;
\t\tpadding: 18px 20px;
\t\tbackground: linear-gradient(180deg, #eff6ff 0%, #dbeafe 100%);
\t\tcolor: #1e3a8a;
\t}
\t.hero h1 {
\t\tmargin: 6px 0 4px;
\t\tfont-size: 22px;
\t}
\t.hero h1 small {
\t\tfont-size: 14px;
\t\tfont-weight: 500;
\t\tcolor: #1e40af;
\t}
\t.sub {
\t\tmargin: 4px 0;
\t\tfont-size: 13px;
\t\topacity: 0.85;
\t}
\t.badge {
\t\tdisplay: inline-block;
\t\tbackground: #1d4ed8;
\t\tcolor: #fff;
\t\tpadding: 2px 8px;
\t\tborder-radius: 10px;
\t\tfont-size: 12px;
\t}
\t.card {
\t\tbackground: #ffffff;
\t\tborder: 1px solid #e2e8f0;
\t\tborder-radius: 12px;
\t\tpadding: 14px 16px;
\t}
\t.card-head h2 {
\t\tmargin: 0 0 8px;
\t\tfont-size: 16px;
\t}
\t.kv {
\t\tdisplay: grid;
\t\tgrid-template-columns: max-content 1fr;
\t\tcolumn-gap: 14px;
\t\trow-gap: 4px;
\t\tmargin: 0;
\t}
\t.kv dt {
\t\tfont-size: 12px;
\t\tcolor: #64748b;
\t}
\t.kv dd {
\t\tmargin: 0;
\t\tfont-size: 13px;
\t}
\t.mono {
\t\tfont-family: ui-monospace, SFMono-Regular, Consolas, monospace;
\t}
\t.btn {
\t\tbackground: #1d4ed8;
\t\tcolor: #fff;
\t\tborder: 0;
\t\tpadding: 6px 14px;
\t\tborder-radius: 6px;
\t\tcursor: pointer;
\t\tfont-size: 13px;
\t}
\t.btn:disabled {
\t\topacity: 0.6;
\t\tcursor: progress;
\t}
\t.out {
\t\tmargin-top: 10px;
\t\tbackground: #0f172a;
\t\tcolor: #e2e8f0;
\t\tpadding: 10px;
\t\tborder-radius: 6px;
\t\tfont-size: 12px;
\t\toverflow-x: auto;
\t}
\t.out.err {
\t\tbackground: #7f1d1d;
\t\tcolor: #fee2e2;
\t}
\tcode {
\t\tbackground: rgba(0, 0, 0, 0.06);
\t\tpadding: 1px 5px;
\t\tborder-radius: 4px;
\t\tfont-family: ui-monospace, SFMono-Regular, Consolas, monospace;
\t\tfont-size: 0.92em;
\t}
\t.rt-foot {
\t\tfont-size: 11px;
\t\tcolor: #94a3b8;
\t\ttext-align: center;
\t\tpadding-top: 4px;
\t}
</style>
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_pascal_case(name: str) -> str:
    """voting -> Voting; member_dashboard -> MemberDashboard."""
    return "".join(seg.capitalize() for seg in name.replace("-", "_").split("_") if seg)


def _read_manifest(ext_dir: Path) -> Optional[dict]:
    manifest_path = ext_dir / "manifest.json"
    if not manifest_path.exists():
        return None
    try:
        with manifest_path.open("r") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        print(f"  ! malformed manifest.json in {ext_dir}: {exc}", file=sys.stderr)
        return None


def _list_extensions(extensions_root: Path, only: Optional[str] = None) -> List[Path]:
    if not extensions_root.is_dir():
        raise FileNotFoundError(f"Extensions root not found: {extensions_root}")
    out: List[Path] = []
    for child in sorted(extensions_root.iterdir()):
        if not child.is_dir():
            continue
        if child.name in SKIP_EXTENSION_IDS:
            continue
        if only and child.name != only:
            continue
        if not (child / "manifest.json").exists():
            print(f"  ! skipping {child.name}: no manifest.json")
            continue
        out.append(child)
    return out


def _scaffold_one(
    ext_dir: Path,
    *,
    force: bool = False,
    quiet: bool = False,
) -> str:
    """Returns one of: 'created', 'overwritten', 'skipped-existing',
    'skipped-protected', 'skipped-no-manifest'."""
    ext_id = ext_dir.name
    manifest = _read_manifest(ext_dir)
    if not manifest:
        return "skipped-no-manifest"

    rt_dir = ext_dir / "frontend-rt"

    if ext_id in PROTECTED_EXTENSION_IDS and rt_dir.exists():
        if not quiet:
            print(f"  · {ext_id}: protected (canonical template) — left untouched")
        return "skipped-protected"

    if rt_dir.exists() and not force:
        if not quiet:
            print(f"  · {ext_id}: frontend-rt/ already exists — skipping (use --force to overwrite)")
        return "skipped-existing"

    version = str(manifest.get("version", "0.0.0"))
    lib_name = _to_pascal_case(ext_id) + "Ext"

    rt_dir.mkdir(parents=True, exist_ok=True)
    (rt_dir / "src").mkdir(parents=True, exist_ok=True)

    (rt_dir / "package.json").write_text(
        PACKAGE_JSON_TMPL.format(ext_id=ext_id, version=version)
    )
    (rt_dir / "tsconfig.json").write_text(TSCONFIG_JSON)
    (rt_dir / "vite.config.ts").write_text(
        VITE_CONFIG_TMPL.format(ext_id=ext_id, lib_name=lib_name)
    )
    (rt_dir / "src" / "index.ts").write_text(INDEX_TS_TMPL)
    (rt_dir / "src" / "Placeholder.svelte").write_text(PLACEHOLDER_SVELTE_TMPL)

    # Friendly README so operators know what to do next.
    readme = (
        f"# {ext_id} — runtime-loadable frontend bundle\n\n"
        "Auto-scaffolded by `scripts/scaffold_runtime_bundles.py`.\n\n"
        "Build:\n\n"
        "```bash\nnpm install\nnpm run build\n```\n\n"
        "The output `dist/index.js` is the ESM bundle that `realm_frontend` "
        "dynamic-imports at runtime. Replace `src/Placeholder.svelte` with "
        "the real UI (it must keep the `mount(target, props)` contract in "
        "`src/index.ts`).\n"
    )
    (rt_dir / "README.md").write_text(readme)

    if not quiet:
        print(f"  + {ext_id}: scaffolded frontend-rt/ (v{version})")
    return "overwritten" if force else "created"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Iterable[str]) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Scaffold per-extension frontend-rt/ directories from the "
            "member_dashboard reference template."
        )
    )
    parser.add_argument(
        "--extensions-repo",
        default=str(DEFAULT_EXTENSIONS_REPO),
        help=f"Path to the realms-extensions checkout (default: {DEFAULT_EXTENSIONS_REPO})",
    )
    parser.add_argument(
        "--only",
        default=None,
        help="Scaffold only this extension id (e.g. voting)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing frontend-rt/ directory (still skips PROTECTED ids)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print which extensions would be scaffolded but do not write files",
    )
    args = parser.parse_args(list(argv))

    extensions_root = Path(args.extensions_repo).expanduser().resolve() / "extensions"
    print(f"Scaffolding from extensions root: {extensions_root}")

    try:
        ext_dirs = _list_extensions(extensions_root, only=args.only)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if not ext_dirs:
        print("No extensions matched.")
        return 0

    summary = {"created": 0, "overwritten": 0, "skipped-existing": 0, "skipped-protected": 0, "skipped-no-manifest": 0}

    for ext_dir in ext_dirs:
        if args.dry_run:
            rt_dir = ext_dir / "frontend-rt"
            already = "exists" if rt_dir.exists() else "absent"
            protected = " [protected]" if ext_dir.name in PROTECTED_EXTENSION_IDS else ""
            print(f"  · {ext_dir.name}: frontend-rt/ {already}{protected}")
            continue
        result = _scaffold_one(ext_dir, force=args.force)
        summary[result] = summary.get(result, 0) + 1

    if not args.dry_run:
        print(
            "\nSummary:"
            f"\n  created:           {summary['created']}"
            f"\n  overwritten:       {summary['overwritten']}"
            f"\n  skipped-existing:  {summary['skipped-existing']}"
            f"\n  skipped-protected: {summary['skipped-protected']}"
            f"\n  skipped-bad:       {summary['skipped-no-manifest']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
