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

## Sample outputs

The snippets below showcase what the CLI produces when it analyzes this repository. Each
example captures a different way to seed the scan so you can compare the ranking
behaviour.

To refresh the captured outputs and keep them in sync with the repository contents, run:

```bash
python scripts/generate_samples.py
```

Pass `--dry-run` to preview the commands or `--only repomap_self_full.txt` (for example)
to limit generation to a subset of the samples.

### Full repository scan

Command:

```bash
python -m repomap_tool.cli --root . --refresh always --map-tokens 800
```

<details>
<summary>Output</summary>

```text
repomap_tool/dump.py:
⋮
│def cvt(s):
⋮

repomap_tool/io.py:
⋮
│class InputOutput:
│    """Minimal IO facade used by the tests and spinner."""
│
⋮
│    def read_text(self, fname: str) -> str:
⋮

repomap_tool/models.py:
⋮
│class Model:
│    """Lightweight stand-in that mimics the bits the repo map expects."""
│
⋮
│    def _normalise_payload(self, payload: Any) -> str:
⋮

repomap_tool/service.py:
⋮
│class RepoMapConsoleIO:
│    """Lightweight console IO adapter compatible with the underlying backend."""
│
⋮
│    def tool_warning(self, *messages) -> None:
⋮
│    def read_text(self, fname: str) -> str:
⋮
│@dataclass
│class RepoMapBuilder:
│    """High-level wrapper that produces repository maps identical to the chat workflow.
│
│    The optional ``model_name`` (or ``main_model``) argument is still supported because
│    the repo map engine sizes its output to the context window of the downstream model.
│    The lightweight :class:`repomap_tool.models.Model` shim lets callers mirror the
│    behaviour of their preferred LLM without pulling in the rest of aider.
⋮
│    def generate_map(
│        self,
│        chat_files: Optional[Sequence[str]] = None,
│        context: Optional[str] = None,
│        mentioned_fnames: Optional[Iterable[str]] = None,
│        mentioned_identifiers: Optional[Iterable[str]] = None,
│        force_refresh: bool = False,
│        include_files: Optional[Sequence[str]] = None,
⋮

repomap_tool/special.py:
⋮
│ROOT_IMPORTANT_FILES = [
│    # Version Control
│    ".gitignore",
│    ".gitattributes",
│    # Documentation
│    "README",
│    "README.md",
│    "README.txt",
│    "README.rst",
│    "CONTRIBUTING",
⋮
│NORMALIZED_ROOT_IMPORTANT_FILES = set(os.path.normpath(path) for path in ROOT_IMPORTANT_FILES)
│
⋮
│def is_important(file_path):
⋮

repomap_tool/spinner.py:
⋮
│try:  # pragma: no cover - optional rich dependency
│    from rich.console import Console
│except ImportError:  # pragma: no cover - exercised implicitly in tests
│    class Console:  # type: ignore[override]
│        """Minimal fallback console when ``rich`` is unavailable."""
│
│        def __init__(self, *args, **kwargs) -> None:  # noqa: D401,ARG002
│            pass
│
│        @property
│        def width(self) -> int:  # noqa: D401
│            return shutil.get_terminal_size((80, 20)).columns
│
│        def show_cursor(self, *_args: object, **_kwargs: object) -> None:  # noqa: D401
⋮

repomap_tool/utils.py:
⋮
│class _BaseTemporaryDirectory(tempfile.TemporaryDirectory):
│    """Temporary directory that cleans up aggressively on exit."""
│
⋮
│    def cleanup(self) -> None:  # pragma: no cover - exercised indirectly in tests
⋮
│class GitTemporaryDirectory(_BaseTemporaryDirectory):
│    """Temporary directory that initialises an empty Git repository on entry."""
│
⋮
│    def cleanup(self) -> None:  # pragma: no cover - exercised indirectly in tests
⋮
│class IgnorantTemporaryDirectory(_BaseTemporaryDirectory):
│    """Temporary directory that swallows common deletion errors."""
│
│    def cleanup(self) -> None:  # pragma: no cover - exercised indirectly in tests
⋮

tests/basic/language_samples.py:
│LANGUAGE_SAMPLES = {'arduino': 'void setup() {\n  Serial.begin(9600);\n}\n\nvoid loop() {\n}\n',
⋮
```

</details>

### Context-driven scan

Command:

```bash
python -m repomap_tool.cli --root . --refresh files --map-tokens 600 \
  --context "Document repo map usage in README"
```

<details>
<summary>Output</summary>

```text
repomap_tool/dump.py:
⋮
│def cvt(s):
⋮

repomap_tool/io.py:
⋮
│class InputOutput:
│    """Minimal IO facade used by the tests and spinner."""
│
⋮
│    def read_text(self, fname: str) -> str:
⋮

repomap_tool/models.py:
⋮
│class Model:
│    """Lightweight stand-in that mimics the bits the repo map expects."""
│
⋮
│    def _normalise_payload(self, payload: Any) -> str:
⋮

repomap_tool/service.py:
⋮
│class RepoMapConsoleIO:
│    """Lightweight console IO adapter compatible with the underlying backend."""
│
⋮
│    def read_text(self, fname: str) -> str:
⋮
│@dataclass
│class RepoMapBuilder:
│    """High-level wrapper that produces repository maps identical to the chat workflow.
│
│    The optional ``model_name`` (or ``main_model``) argument is still supported because
│    the repo map engine sizes its output to the context window of the downstream model.
│    The lightweight :class:`repomap_tool.models.Model` shim lets callers mirror the
│    behaviour of their preferred LLM without pulling in the rest of aider.
⋮
│    def generate_map(
│        self,
│        chat_files: Optional[Sequence[str]] = None,
│        context: Optional[str] = None,
│        mentioned_fnames: Optional[Iterable[str]] = None,
│        mentioned_identifiers: Optional[Iterable[str]] = None,
│        force_refresh: bool = False,
│        include_files: Optional[Sequence[str]] = None,
⋮

repomap_tool/special.py:
⋮
│ROOT_IMPORTANT_FILES = [
│    # Version Control
│    ".gitignore",
│    ".gitattributes",
│    # Documentation
│    "README",
│    "README.md",
│    "README.txt",
│    "README.rst",
│    "CONTRIBUTING",
⋮
│NORMALIZED_ROOT_IMPORTANT_FILES = set(os.path.normpath(path) for path in ROOT_IMPORTANT_FILES)
│
⋮
│def is_important(file_path):
⋮

repomap_tool/spinner.py:
⋮
│try:  # pragma: no cover - optional rich dependency
│    from rich.console import Console
│except ImportError:  # pragma: no cover - exercised implicitly in tests
│    class Console:  # type: ignore[override]
│        """Minimal fallback console when ``rich`` is unavailable."""
│
│        def __init__(self, *args, **kwargs) -> None:  # noqa: D401,ARG002
│            pass
│
│        @property
│        def width(self) -> int:  # noqa: D401
│            return shutil.get_terminal_size((80, 20)).columns
│
│        def show_cursor(self, *_args: object, **_kwargs: object) -> None:  # noqa: D401
⋮

tests/basic/language_samples.py:
│LANGUAGE_SAMPLES = {'arduino': 'void setup() {\n  Serial.begin(9600);\n}\n\nvoid loop() {\n}\n',
⋮
```

</details>

### Chat file primed scan

Command:

```bash
python -m repomap_tool.cli --root . --refresh files --map-tokens 600 \
  --chat-file README.md
```

<details>
<summary>Output</summary>

```text
repomap_tool/dump.py:
⋮
│def cvt(s):
⋮

repomap_tool/io.py:
⋮
│class InputOutput:
│    """Minimal IO facade used by the tests and spinner."""
│
⋮
│    def read_text(self, fname: str) -> str:
⋮

repomap_tool/models.py:
⋮
│class Model:
│    """Lightweight stand-in that mimics the bits the repo map expects."""
│
⋮
│    def _normalise_payload(self, payload: Any) -> str:
⋮

repomap_tool/service.py:
⋮
│class RepoMapConsoleIO:
│    """Lightweight console IO adapter compatible with the underlying backend."""
│
⋮
│    def read_text(self, fname: str) -> str:
⋮
│@dataclass
│class RepoMapBuilder:
│    """High-level wrapper that produces repository maps identical to the chat workflow.
│
│    The optional ``model_name`` (or ``main_model``) argument is still supported because
│    the repo map engine sizes its output to the context window of the downstream model.
│    The lightweight :class:`repomap_tool.models.Model` shim lets callers mirror the
│    behaviour of their preferred LLM without pulling in the rest of aider.
⋮
│    def generate_map(
│        self,
│        chat_files: Optional[Sequence[str]] = None,
│        context: Optional[str] = None,
│        mentioned_fnames: Optional[Iterable[str]] = None,
│        mentioned_identifiers: Optional[Iterable[str]] = None,
│        force_refresh: bool = False,
│        include_files: Optional[Sequence[str]] = None,
⋮

repomap_tool/special.py:
⋮
│ROOT_IMPORTANT_FILES = [
│    # Version Control
│    ".gitignore",
│    ".gitattributes",
│    # Documentation
│    "README",
│    "README.md",
│    "README.txt",
│    "README.rst",
│    "CONTRIBUTING",
⋮
│NORMALIZED_ROOT_IMPORTANT_FILES = set(os.path.normpath(path) for path in ROOT_IMPORTANT_FILES)
│
⋮
│def is_important(file_path):
⋮

repomap_tool/spinner.py:
⋮
│try:  # pragma: no cover - optional rich dependency
│    from rich.console import Console
│except ImportError:  # pragma: no cover - exercised implicitly in tests
│    class Console:  # type: ignore[override]
│        """Minimal fallback console when ``rich`` is unavailable."""
│
│        def __init__(self, *args, **kwargs) -> None:  # noqa: D401,ARG002
│            pass
│
│        @property
│        def width(self) -> int:  # noqa: D401
│            return shutil.get_terminal_size((80, 20)).columns
│
│        def show_cursor(self, *_args: object, **_kwargs: object) -> None:  # noqa: D401
⋮

tests/basic/language_samples.py:
│LANGUAGE_SAMPLES = {'arduino': 'void setup() {\n  Serial.begin(9600);\n}\n\nvoid loop() {\n}\n',
⋮
```

</details>

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
