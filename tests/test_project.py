import json
from worklog import project, config


def test_resolve_from_claude_md(tmp_path):
    (tmp_path / "CLAUDE.md").write_text(
        '# repo\nworklog-project: "content.fans"\n', encoding="utf-8"
    )
    name, source = project.resolve_project(tmp_path, config.DEFAULTS)
    assert name == "content.fans"
    assert source == "claude_md"


def test_resolve_from_local_json(tmp_path):
    d = tmp_path / ".claude"
    d.mkdir()
    (d / "worklog.local.json").write_text('{"project": "TruckingBrief"}', encoding="utf-8")
    name, source = project.resolve_project(tmp_path, config.DEFAULTS)
    assert name == "TruckingBrief"
    assert source == "local_json"


def test_resolve_from_alias_map(tmp_path):
    cfg = dict(config.DEFAULTS)
    cfg["aliases"] = {tmp_path.name: "CU Kazakhstan"}
    name, source = project.resolve_project(tmp_path, cfg)
    assert name == "CU Kazakhstan"
    assert source == "alias"


def test_resolve_unknown_returns_none(tmp_path):
    name, source = project.resolve_project(tmp_path, config.DEFAULTS)
    assert name is None
    assert source == "ask"


def test_init_writes_marker_instruction_localjson_and_config(tmp_path, worklog_home):
    project.init_project(tmp_path, "content.fans", config.load_config())
    claude_md = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert 'worklog-project: "content.fans"' in claude_md
    assert "worklog" in claude_md.lower()
    local = json.loads(
        (tmp_path / ".claude" / "worklog.local.json").read_text(encoding="utf-8")
    )
    assert local["project"] == "content.fans"
    assert "content.fans" in config.load_config()["known_projects"]


def test_init_is_idempotent(tmp_path, worklog_home):
    project.init_project(tmp_path, "content.fans", config.load_config())
    project.init_project(tmp_path, "content.fans", config.load_config())
    claude_md = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert claude_md.count('worklog-project: "content.fans"') == 1
    assert config.load_config()["known_projects"].count("content.fans") == 1
