from __future__ import annotations

from pathlib import Path

import git

from repomap_tool.mcp.server import (
    create_server,
    generate_ranked_tags_tool,
    generate_repo_map_tool,
)


def _seed_repository(path: Path) -> None:
    repo = git.Repo.init(path)
    file_a = path / "alpha.py"
    file_b = path / "beta.py"
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


def test_generate_repo_map_tool(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _seed_repository(repo_root)

    result = generate_repo_map_tool(root=str(repo_root))

    assert "alpha.py" in result
    assert "beta.py" in result


def test_generate_ranked_tags_tool(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _seed_repository(repo_root)

    tags = generate_ranked_tags_tool(root=str(repo_root), limit=2)

    assert len(tags) <= 2
    assert tags, "Expected ranked tags to be returned"
    first = tags[0]
    assert first.file.endswith(".py")
    assert isinstance(first.line, int)
    assert first.name


def test_create_server_registers_tools():
    server = create_server()
    tool_names = {tool.name for tool in server._tool_manager.list_tools()}

    assert {"generate_repo_map", "generate_ranked_tags"}.issubset(tool_names)


def test_generate_repo_map_tool_uses_default_root(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _seed_repository(repo_root)

    try:
        create_server(default_root=repo_root)
        result = generate_repo_map_tool()
    finally:
        create_server(default_root=None)

    assert "alpha.py" in result
    assert "beta.py" in result

