from __future__ import annotations

from pathlib import Path

import git

import pytest

from repomap_tool.mcp.server import (
    build_arg_parser,
    create_server,
    generate_ranked_tags_tool,
    generate_repo_map_tool,
    main,
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
    if first.name is not None:
        assert isinstance(first.line, int)
    else:
        assert first.line is None


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


def test_create_server_respects_log_level():
    server = create_server(log_level="debug")

    assert server.settings.log_level == "DEBUG"


def test_create_server_rejects_invalid_log_level():
    with pytest.raises(ValueError):
        create_server(log_level="nope")


def test_build_arg_parser_normalises_log_level():
    parser = build_arg_parser()
    args = parser.parse_args(["--log-level", "debug"])

    assert args.log_level == "DEBUG"


def test_main_handles_keyboard_interrupt(monkeypatch, capsys):
    def fake_run(*_args, **_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr("repomap_tool.mcp.server.anyio.run", fake_run)

    exit_code = main(["--transport", "stdio"])

    captured = capsys.readouterr()
    assert "awaiting MCP client handshake on stdio" in captured.err
    assert "interrupted by user" in captured.err
    assert exit_code == 130

