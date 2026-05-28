# Releasing stumblestack

The release primitive is a **signed, annotated git tag**. stumblestack is **not
published to PyPI** — consumers install the MCP server from a pinned git ref
(see `mcp-server/README.md`). The project version (`vX.Y.Z` tag) and the Python
package version in `mcp-server/pyproject.toml` are intentionally decoupled.

## Preconditions

- `main` is green: `make check` passes locally and all required CI checks are green.
- `index.json` is up to date and committed: `python3 scripts/build_index.py && git diff --exit-code index.json`.
- A GPG (or SSH) signing key is configured: `git config user.signingkey ...` and
  `git config commit.gpgsign true` (or `gpg.format ssh`).

## Steps

1. **Move the CHANGELOG.** Promote `## [Unreleased]` content into a new
   `## [X.Y.Z] - YYYY-MM-DD` section. Commit:
   ```
   git commit -am "docs: changelog for vX.Y.Z"
   ```
2. **Final gate replay:**
   ```
   make check && python3 scripts/index_check.py --new index.json
   ```
3. **Tag (signed, annotated):**
   ```
   git tag -s vX.Y.Z -m "stumblestack vX.Y.Z"
   git tag -v vX.Y.Z          # verify the signature
   ```
4. **Push the tag:**
   ```
   git push origin vX.Y.Z
   ```
5. Pushing a `v*` tag triggers `.github/workflows/sign-index.yml` (manual /
   tag-gated), which produces a cosign bundle for `index.json` and attaches it to
   the GitHub Release. Signing is a maintainer step; CI cannot mint the tag.

## Consuming a pinned release

```
pip install "stumblestack-mcp @ git+https://github.com/Wisdoverse/stumblestack.git@vX.Y.Z#subdirectory=mcp-server"
```

## Yanking

Tags are immutable references; do not delete a published tag. To withdraw a
release, publish a follow-up tag with a CHANGELOG `### Removed`/`### Fixed` note
explaining the issue.
