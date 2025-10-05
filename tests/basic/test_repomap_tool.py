import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import git

from repomap_tool.cli import main as repomap_main
from repomap_tool.service import RepoMapBuilder


class TestRepoMapBuilder(unittest.TestCase):
    def _seed_repository(self, path: str) -> None:
        repo = git.Repo.init(path)
        file_a = Path(path) / "alpha.py"
        file_b = Path(path) / "beta.py"
        file_a.write_text(
            """
import beta

def alpha():
    return beta.beta()
"""
        )
        file_b.write_text(
            """
def beta():
    return 42
"""
        )
        repo.index.add(["alpha.py", "beta.py"])
        repo.index.commit("initial commit")

    def test_service_generates_map(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self._seed_repository(temp_dir)
            service = RepoMapBuilder(root=temp_dir)
            result = service.generate_map()
            self.assertIn("alpha.py", result)
            self.assertIn("beta.py", result)

    def test_cli_outputs_map(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self._seed_repository(temp_dir)
            args = ["--root", temp_dir]
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = repomap_main(args)
            output = stdout.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("alpha.py", output)

    def test_builder_accepts_custom_model_name(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self._seed_repository(temp_dir)
            service = RepoMapBuilder(root=temp_dir, model_name="custom-ctx", map_tokens=1234)
            self.assertEqual(service.main_model.name, "custom-ctx")
            self.assertEqual(service.map_tokens, 1234)
            result = service.generate_map()
            self.assertIn("beta.py", result)

    def test_context_highlights_specific_file(self):
        """The builder should surface code for files mentioned in the context."""

        with tempfile.TemporaryDirectory() as temp_dir:
            self._seed_repository(temp_dir)
            service = RepoMapBuilder(root=temp_dir)
            result = service.generate_map(context="alpha.py")
            self.assertIn("alpha.py", result)
            self.assertIn("│def alpha():", result)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
