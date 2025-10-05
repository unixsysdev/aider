
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

