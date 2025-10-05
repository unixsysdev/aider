# repomap-tool

`repomap-tool` is a self-contained toolkit for generating the same repository maps and
ranked tag listings that power the original aider chat workflow.  It vendors the
Tree-sitter queries, caching logic and ranking heuristics so you can embed the
context building pipeline inside any project without depending on the rest of aider.

## Installation

```bash
# Install directly from the subdirectory in this repository
python -m pip install ./repomap_tool
```

The package bundles the Tree-sitter query data files so no extra setup is required.

## Command line usage

The package ships with a small CLI entry point:

```bash
repomap-tool --root /path/to/repo --chat-file src/main.py --context "fix login"
```

Options include:

- `--root` – repository root (defaults to the current directory)
- `--map-tokens` – override the token budget used when formatting the map
- `--refresh` – control how aggressively cached results are reused
- `--chat-file` / `--context` / `--context-file` – seed the ranking with files or text
- `--mention` / `--ident` – mark extra files or identifiers as already mentioned
- `--include` – add untracked files to the scan

Run `repomap-tool --help` to see the complete list.

## Python API

```python
from repomap_tool import RepoMapBuilder

builder = RepoMapBuilder(
    root="/path/to/repo",
    model_name="custom-16k",  # optional, see below
    map_tokens=2048,
)

repo_map = builder.generate_map(
    chat_files=["src/main.py"],
    context="Investigate login failures",
    mentioned_identifiers=["LoginController"],
)
```

The builder exposes the same `generate_map` and `generate_ranked_tags` helpers used in the
chat application, plus a convenience `build_repo_map` function for quick one-shot usage.

### Why models still matter

The repo map engine needs an estimate of how many tokens are available when rendering
context for a model.  The bundled `Model` shim provides that estimate without talking to
an actual LLM provider.  Supplying your own `Model` (or passing `model_name="..."`) lets
you align the map budget with the context window of the model that will consume it.  For
example, you can configure a larger budget when targeting a 32k-token model or tighten it
for smaller models to avoid overflowing their context limits.

If you already track token usage in your project, pass a custom `Model` instance with a
bespoke `token_counter` so repo map sizing matches your production heuristics exactly.

## Caching

Repository maps are cached under `.repomap_tool.tags.cache.v*` inside each repository to
avoid re-running expensive Tree-sitter queries.  Use `--refresh` or `--force-refresh`
when you want to bypass or invalidate cached data.

## License

The toolkit inherits the Apache 2.0 license from aider.  See `../LICENSE.txt` for the
full text.
