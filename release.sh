#!/usr/bin/env bash
# Build a release wheel + sdist. Refuses to run on a dirty or untagged tree.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

# 1. Clean working tree
if [[ -n "$(git status --porcelain)" ]]; then
    echo "✗ working tree dirty — commit or stash before releasing" >&2
    exit 1
fi

# 2. HEAD is on a tag
TAG=$(git describe --exact-match --tags HEAD 2>/dev/null || true)
if [[ -z "$TAG" ]]; then
    echo "✗ HEAD is not on a tag." >&2
    echo "  Tag first:  git tag -a vX.Y.Z -m 'release notes here'" >&2
    exit 1
fi

# 3. Tag matches semver-ish vX.Y.Z
if ! [[ "$TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "✗ tag $TAG does not match vX.Y.Z" >&2
    exit 1
fi

# 4. Build
rm -rf dist/ build/
.venv/bin/python -m build

# 5. Confirm wheel filename matches tag
EXPECTED="lwt_wiki-${TAG#v}-py3-none-any.whl"
if [[ ! -f "dist/$EXPECTED" ]]; then
    echo "✗ expected dist/$EXPECTED but got:" >&2
    ls dist/ >&2
    exit 1
fi

echo
echo "✓ Built $EXPECTED"
ls -la dist/
