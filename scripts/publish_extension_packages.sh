#!/usr/bin/env bash
# Publish the extension packages (packages/extension-bridge, packages/extension-ui)
# to npm. Package names/versions are read from each package.json.
#
# Usage:
#   NPM_TOKEN=npm_xxx ./scripts/publish_extension_packages.sh
#   # or, if already logged in via `npm login`:
#   ./scripts/publish_extension_packages.sh
#   # experimental channel (install via `npm i @realmsgos/extension-bridge@next`):
#   NPM_TAG=next NPM_TOKEN=npm_xxx ./scripts/publish_extension_packages.sh
#
# Notes:
# - NPM_TOKEN is passed to npm through a temporary, isolated npmrc that is
#   deleted on exit; your ~/.npmrc is never touched.
# - Scoped packages are published with --access public.
# - Idempotent: a name@version that already exists on the registry is skipped.
# - Safety: only packages named ${REQUIRED_SCOPE}/* with a valid non-empty
#   semver version are ever published; npm is always run from inside the
#   package directory so a stray cwd can never publish the monorepo root.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGES=("extension-bridge" "extension-ui")
REQUIRED_SCOPE="${REQUIRED_SCOPE:-@realmsgos}"
TAG="${NPM_TAG:-latest}"

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
echo "Publishing to npm as: $(npm whoami) (dist-tag: $TAG)"

for pkg in "${PACKAGES[@]}"; do
	dir="$REPO_ROOT/packages/$pkg"
	name="$(node -p "require('$dir/package.json').name")"
	version="$(node -p "require('$dir/package.json').version")"

	if [[ "$name" != "$REQUIRED_SCOPE"/* ]]; then
		echo "error: refusing to publish '$name' — must be scoped under $REQUIRED_SCOPE/" >&2
		exit 1
	fi
	if ! [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+([-+][0-9A-Za-z.-]+)?$ ]]; then
		echo "error: '$name' has invalid or empty version '$version' in $dir/package.json" >&2
		exit 1
	fi

	if npm view "$name@$version" version >/dev/null 2>&1; then
		echo "skip: $name@$version is already published"
		continue
	fi

	echo "==> building $name@$version"
	if [[ "$pkg" == "extension-ui" ]]; then
		# Svelte 5 components: build via workspace so svelte2tsx resolves Svelte 5
		# (isolated install in packages/extension-ui hoists Svelte 4 from other workspaces).
		(
			cd "$REPO_ROOT"
			npm install --no-audit --no-fund
			npm run build -w "$name"
		)
	else
		(
			cd "$dir"
			npm install --no-audit --no-fund
			npm run build
		)
	fi

	echo "==> publishing $name@$version (tag: $TAG)"
	(
		cd "$dir"
		npm publish --access public --tag "$TAG"
	)
	# npm's read CDN lags writes by a few seconds; retry the verification.
	verified=""
	for _ in $(seq 1 10); do
		if verified="$(npm view "$name@$version" version 2>/dev/null)"; then
			break
		fi
		sleep 3
	done
	if [[ -z "$verified" ]]; then
		echo "error: $name@$version not visible on the registry 30s after publish" >&2
		exit 1
	fi
	echo "    published: $verified — https://www.npmjs.com/package/$name/v/$version"
done

echo "All done."
