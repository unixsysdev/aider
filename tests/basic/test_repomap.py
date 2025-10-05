import os
import time
import unittest
from pathlib import Path

import git

from repomap_tool.dump import dump  # noqa: F401
from repomap_tool.io import InputOutput
from repomap_tool.models import Model
from repomap_tool.repomap import RepoMap
from repomap_tool.utils import GitTemporaryDirectory, IgnorantTemporaryDirectory
from .language_samples import LANGUAGE_SAMPLES


class TestRepoMap(unittest.TestCase):
    def setUp(self):
        self.GPT35 = Model("gpt-3.5-turbo")

    def test_get_repo_map(self):
        # Create a temporary directory with sample files for testing
        test_files = [
            "test_file1.py",
            "test_file2.py",
            "test_file3.md",
            "test_file4.json",
        ]

        with IgnorantTemporaryDirectory() as temp_dir:
            for file in test_files:
                with open(os.path.join(temp_dir, file), "w") as f:
                    f.write("")

            io = InputOutput()
            repo_map = RepoMap(main_model=self.GPT35, root=temp_dir, io=io)
            other_files = [os.path.join(temp_dir, file) for file in test_files]
            result = repo_map.get_repo_map([], other_files)

            # Check if the result contains the expected tags map
            self.assertIn("test_file1.py", result)
            self.assertIn("test_file2.py", result)
            self.assertIn("test_file3.md", result)
            self.assertIn("test_file4.json", result)

            # close the open cache files, so Windows won't error
            del repo_map

    def test_repo_map_refresh_files(self):
        with GitTemporaryDirectory() as temp_dir:
            repo = git.Repo(temp_dir)

            # Create three source files with one function each
            file1_content = "def function1():\n    return 'Hello from file1'\n"
            file2_content = "def function2():\n    return 'Hello from file2'\n"
            file3_content = "def function3():\n    return 'Hello from file3'\n"

            with open(os.path.join(temp_dir, "file1.py"), "w") as f:
                f.write(file1_content)
            with open(os.path.join(temp_dir, "file2.py"), "w") as f:
                f.write(file2_content)
            with open(os.path.join(temp_dir, "file3.py"), "w") as f:
                f.write(file3_content)

            # Add files to git
            repo.index.add(["file1.py", "file2.py", "file3.py"])
            repo.index.commit("Initial commit")

            # Initialize RepoMap with refresh="files"
            io = InputOutput()
            repo_map = RepoMap(main_model=self.GPT35, root=temp_dir, io=io, refresh="files")
            other_files = [
                os.path.join(temp_dir, "file1.py"),
                os.path.join(temp_dir, "file2.py"),
                os.path.join(temp_dir, "file3.py"),
            ]

            # Get initial repo map
            initial_map = repo_map.get_repo_map([], other_files)
            dump(initial_map)
            self.assertIn("function1", initial_map)
            self.assertIn("function2", initial_map)
            self.assertIn("function3", initial_map)

            # Add a new function to file1.py
            with open(os.path.join(temp_dir, "file1.py"), "a") as f:
                f.write("\ndef functionNEW():\n    return 'Hello NEW'\n")

            # Get another repo map
            second_map = repo_map.get_repo_map([], other_files)
            self.assertEqual(
                initial_map, second_map, "RepoMap should not change with refresh='files'"
            )

            other_files = [
                os.path.join(temp_dir, "file1.py"),
                os.path.join(temp_dir, "file2.py"),
            ]
            second_map = repo_map.get_repo_map([], other_files)
            self.assertIn("functionNEW", second_map)

            # close the open cache files, so Windows won't error
            del repo_map
            del repo

    def test_repo_map_refresh_auto(self):
        with GitTemporaryDirectory() as temp_dir:
            repo = git.Repo(temp_dir)

            # Create two source files with one function each
            file1_content = "def function1():\n    return 'Hello from file1'\n"
            file2_content = "def function2():\n    return 'Hello from file2'\n"

            with open(os.path.join(temp_dir, "file1.py"), "w") as f:
                f.write(file1_content)
            with open(os.path.join(temp_dir, "file2.py"), "w") as f:
                f.write(file2_content)

            # Add files to git
            repo.index.add(["file1.py", "file2.py"])
            repo.index.commit("Initial commit")

            # Initialize RepoMap with refresh="auto"
            io = InputOutput()
            repo_map = RepoMap(main_model=self.GPT35, root=temp_dir, io=io, refresh="auto")
            chat_files = []
            other_files = [os.path.join(temp_dir, "file1.py"), os.path.join(temp_dir, "file2.py")]

            # Force the RepoMap computation to take more than 1 second
            original_get_ranked_tags = repo_map.get_ranked_tags

            def slow_get_ranked_tags(*args, **kwargs):
                time.sleep(1.1)  # Sleep for 1.1 seconds to ensure it's over 1 second
                return original_get_ranked_tags(*args, **kwargs)

            repo_map.get_ranked_tags = slow_get_ranked_tags

            # Get initial repo map
            initial_map = repo_map.get_repo_map(chat_files, other_files)
            self.assertIn("function1", initial_map)
            self.assertIn("function2", initial_map)
            self.assertNotIn("functionNEW", initial_map)

            # Add a new function to file1.py
            with open(os.path.join(temp_dir, "file1.py"), "a") as f:
                f.write("\ndef functionNEW():\n    return 'Hello NEW'\n")

            # Get another repo map without force_refresh
            second_map = repo_map.get_repo_map(chat_files, other_files)
            self.assertEqual(
                initial_map, second_map, "RepoMap should not change without force_refresh"
            )

            # Get a new repo map with force_refresh
            final_map = repo_map.get_repo_map(chat_files, other_files, force_refresh=True)
            self.assertIn("functionNEW", final_map)
            self.assertNotEqual(initial_map, final_map, "RepoMap should change with force_refresh")

            # close the open cache files, so Windows won't error
            del repo_map
            del repo

    def test_get_repo_map_with_identifiers(self):
        # Create a temporary directory with a sample Python file containing identifiers
        test_file1 = "test_file_with_identifiers.py"
        file_content1 = """\
class MyClass:
    def my_method(self, arg1, arg2):
        return arg1 + arg2

def my_function(arg1, arg2):
    return arg1 * arg2
"""

        test_file2 = "test_file_import.py"
        file_content2 = """\
from test_file_with_identifiers import MyClass

obj = MyClass()
print(obj.my_method(1, 2))
print(my_function(3, 4))
"""

        test_file3 = "test_file_pass.py"
        file_content3 = "pass"

        with IgnorantTemporaryDirectory() as temp_dir:
            with open(os.path.join(temp_dir, test_file1), "w") as f:
                f.write(file_content1)

            with open(os.path.join(temp_dir, test_file2), "w") as f:
                f.write(file_content2)

            with open(os.path.join(temp_dir, test_file3), "w") as f:
                f.write(file_content3)

            io = InputOutput()
            repo_map = RepoMap(main_model=self.GPT35, root=temp_dir, io=io)
            other_files = [
                os.path.join(temp_dir, test_file1),
                os.path.join(temp_dir, test_file2),
                os.path.join(temp_dir, test_file3),
            ]
            result = repo_map.get_repo_map([], other_files)

            # Check if the result contains the expected tags map with identifiers
            self.assertIn("test_file_with_identifiers.py", result)
            self.assertIn("MyClass", result)
            self.assertIn("my_method", result)
            self.assertIn("my_function", result)
            self.assertIn("test_file_pass.py", result)

            # close the open cache files, so Windows won't error
            del repo_map

    def test_get_repo_map_all_files(self):
        test_files = [
            "test_file0.py",
            "test_file1.txt",
            "test_file2.md",
            "test_file3.json",
            "test_file4.html",
            "test_file5.css",
            "test_file6.js",
        ]

        with IgnorantTemporaryDirectory() as temp_dir:
            for file in test_files:
                with open(os.path.join(temp_dir, file), "w") as f:
                    f.write("")

            repo_map = RepoMap(main_model=self.GPT35, root=temp_dir, io=InputOutput())

            other_files = [os.path.join(temp_dir, file) for file in test_files]
            result = repo_map.get_repo_map([], other_files)
            dump(other_files)
            dump(repr(result))

            # Check if the result contains each specific file in the expected tags map without ctags
            for file in test_files:
                self.assertIn(file, result)

            # close the open cache files, so Windows won't error
            del repo_map

    def test_get_repo_map_excludes_added_files(self):
        # Create a temporary directory with sample files for testing
        test_files = [
            "test_file1.py",
            "test_file2.py",
            "test_file3.md",
            "test_file4.json",
        ]

        with IgnorantTemporaryDirectory() as temp_dir:
            for file in test_files:
                with open(os.path.join(temp_dir, file), "w") as f:
                    f.write("def foo(): pass\n")

            io = InputOutput()
            repo_map = RepoMap(main_model=self.GPT35, root=temp_dir, io=io)
            test_files = [os.path.join(temp_dir, file) for file in test_files]
            result = repo_map.get_repo_map(test_files[:2], test_files[2:])

            dump(result)

            # Check if the result contains the expected tags map
            self.assertNotIn("test_file1.py", result)
            self.assertNotIn("test_file2.py", result)
            self.assertIn("test_file3.md", result)
            self.assertIn("test_file4.json", result)

            # close the open cache files, so Windows won't error
            del repo_map


class TestRepoMapTypescript(unittest.TestCase):
    def setUp(self):
        self.GPT35 = Model("gpt-3.5-turbo")


class TestRepoMapAllLanguages(unittest.TestCase):
    def setUp(self):
        self.GPT35 = Model("gpt-3.5-turbo")

    def test_language_c(self):
        self._test_language_repo_map("c", "c", "main")

    def test_language_cpp(self):
        self._test_language_repo_map("cpp", "cpp", "main")

    def test_language_d(self):
        self._test_language_repo_map("d", "d", "main")

    def test_language_dart(self):
        self._test_language_repo_map("dart", "dart", "Person")

    def test_language_elixir(self):
        self._test_language_repo_map("elixir", "ex", "Greeter")

    def test_language_gleam(self):
        self._test_language_repo_map("gleam", "gleam", "greet")

    def test_language_java(self):
        self._test_language_repo_map("java", "java", "Greeting")

    def test_language_javascript(self):
        self._test_language_repo_map("javascript", "js", "Person")

    def test_language_kotlin(self):
        self._test_language_repo_map("kotlin", "kt", "Greeting")

    def test_language_lua(self):
        self._test_language_repo_map("lua", "lua", "greet")

    def test_language_php(self):
        self._test_language_repo_map("php", "php", "greet")

    def test_language_python(self):
        self._test_language_repo_map("python", "py", "Person")

    # "ql": ("ql", "greet"), # not supported in tsl-pack (yet?)

    def test_language_ruby(self):
        self._test_language_repo_map("ruby", "rb", "greet")

    def test_language_rust(self):
        self._test_language_repo_map("rust", "rs", "Person")

    def test_language_typescript(self):
        self._test_language_repo_map("typescript", "ts", "greet")

    def test_language_tsx(self):
        self._test_language_repo_map("tsx", "tsx", "UserProps")

    def test_language_csharp(self):
        self._test_language_repo_map("csharp", "cs", "IGreeter")

    def test_language_elisp(self):
        self._test_language_repo_map("elisp", "el", "greeter")

    def test_language_elm(self):
        self._test_language_repo_map("elm", "elm", "Person")

    def test_language_go(self):
        self._test_language_repo_map("go", "go", "Greeter")

    def test_language_hcl(self):
        self._test_language_repo_map("hcl", "tf", "aws_vpc")

    def test_language_arduino(self):
        self._test_language_repo_map("arduino", "ino", "setup")

    def test_language_chatito(self):
        self._test_language_repo_map("chatito", "chatito", "intent")

    def test_language_clojure(self):
        self._test_language_repo_map("clojure", "clj", "greet")

    def test_language_commonlisp(self):
        self._test_language_repo_map("commonlisp", "lisp", "greet")

    def test_language_pony(self):
        self._test_language_repo_map("pony", "pony", "Greeter")

    def test_language_properties(self):
        self._test_language_repo_map("properties", "properties", "database.url")

    def test_language_r(self):
        self._test_language_repo_map("r", "r", "calculate")

    def test_language_racket(self):
        self._test_language_repo_map("racket", "rkt", "greet")

    def test_language_solidity(self):
        self._test_language_repo_map("solidity", "sol", "SimpleStorage")

    def test_language_swift(self):
        self._test_language_repo_map("swift", "swift", "Greeter")

    def test_language_udev(self):
        self._test_language_repo_map("udev", "rules", None)

    def test_language_scala(self):
        self._test_language_repo_map("scala", "scala", "Greeter")

    def test_language_ocaml(self):
        self._test_language_repo_map("ocaml", "ml", "Greeter")

    def test_language_ocaml_interface(self):
        self._test_language_repo_map("ocaml_interface", "mli", "greet")

    def test_language_matlab(self):
        self._test_language_repo_map("matlab", "m", "Person")

    def _test_language_repo_map(self, lang, key, symbol):
        """Helper method to test repo map generation for a specific language."""
        filename = f"test.{key}"
        content = LANGUAGE_SAMPLES.get(lang)
        if not content:
            self.fail(f"Language sample missing for {lang}")
        with GitTemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, filename)
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(content)

            io = InputOutput()
            repo_map = RepoMap(main_model=self.GPT35, root=temp_dir, io=io)
            other_files = [test_file]
            result = repo_map.get_repo_map([], other_files)
            dump(lang)
            dump(result)

            print(result)
            lines = [line for line in result.strip().splitlines() if line]
            if symbol:
                self.assertGreater(len(lines), 1)
            else:
                self.assertGreaterEqual(len(lines), 1)

            # Check if the result contains all the expected files and symbols
            self.assertIn(
                filename, result, f"File for language {lang} not found in repo map: {result}"
            )
            if symbol:
                self.assertIn(
                    symbol,
                    result,
                    f"Key symbol '{symbol}' for language {lang} not found in repo map: {result}",
                )

            # close the open cache files, so Windows won't error
            del repo_map

    def test_repo_map_sample_code_base(self):
        with IgnorantTemporaryDirectory() as sample_dir:
            sample_root = Path(sample_dir)
            backend = sample_root / "backend" / "app.py"
            frontend = sample_root / "frontend" / "ui.tsx"
            docs = sample_root / "README.md"

            backend.parent.mkdir(parents=True, exist_ok=True)
            frontend.parent.mkdir(parents=True, exist_ok=True)

            backend.write_text(
                """from fastapi import FastAPI\n\napp = FastAPI()\n\n\n@app.get('/ping')\ndef handler() -> dict[str, str]:\n    return {"status": "ok"}\n""",
                encoding="utf-8",
            )
            frontend.write_text(
                """import React from 'react';\n\nexport const App: React.FC = () => <div>Dashboard</div>;\n""",
                encoding="utf-8",
            )
            docs.write_text("# Sample project\n\nThis project exercises RepoMap.\n", encoding="utf-8")

            repo_map = RepoMap(main_model=self.GPT35, root=sample_dir, io=InputOutput())
            other_files = [str(p) for p in sample_root.rglob("*") if p.is_file()]
            generated_map = repo_map.get_repo_map([], other_files)

            self.assertIsNotNone(generated_map)
            self.assertIn("backend/app.py", generated_map)
            self.assertIn("handler", generated_map)
            self.assertIn("frontend/ui.tsx", generated_map)
            self.assertGreater(len(generated_map.strip().splitlines()), 3)


if __name__ == "__main__":
    unittest.main()
