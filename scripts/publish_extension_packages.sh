#!/usr/bin/env bash
# Publish the extension packages (packages/extension-bridge, packages/extension-ui)
# to npm. Package names/versions are read from each package.json.
#
# Usage:
#   NPM_TOKEN=npm_xxx ./scripts/publish_extension_packages.sh
#   # or, if already logged in via `npm login`:
#   ./scripts/publish_extension_packages.sh
#
# Notes:
# - NPM_TOKEN is passed to npm through a temporary, isolated npmrc that is
#   deleted on exit; your ~/.npmrc is never touched.
# - Scoped packages are published with --access public.
# - Idempotent: a name@version that already exists on the registry is skipped.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGES=("extension-bridge" "extension-ui")

NPMRC_TMP=""
if [[ -n "${NPM_TOKEN:-}" ]]; then
	NPMRC_TMP="$(mktemp)"
	trap 'rm -f "$NPMRC_TMP"' EXIT
	echo "//registry.npmjs.org/:_authToken=${NPM_TOKEN}" >"$NPMRC_TMP"
	export NPM_CONFIG_USERCONFIG="$NPMRC_TMP"
fi

if ! npm whoami >/dev/null 2>&1; then
	echo "error: npm authentication failed." >&2
	echo "  Export NPM_TOKEN (automation token) or run 'npm login' first." >&2
	exit 1
fi
echo "Publishing to npm as: $(npm whoami)"

for pkg in "${PACKAGES[@]}"; do
	dir="$REPO_ROOT/packages/$pkg"
	name="$(node -p "require('$dir/package.json').name")"
	version="$(node -p "require('$dir/package.json').version")"

	if npm view "$name@$version" version >/dev/null 2>&1; then
		echo "skip: $name@$version is already published"
		continue
	fi

	echo "==> building $name@$version"
	npm --prefix "$dir" install --no-audit --no-fund
	npm --prefix "$dir" run build

	echo "==> publishing $name@$version"
	npm --prefix "$dir" publish --access public
	echo "    published: $(npm view "$name@$version" version)"
done

echo "All done."
