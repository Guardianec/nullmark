import json
import subprocess
import sys


def cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "nullmark", *map(str, args)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_cli_help_and_version():
    assert cli("--help").returncode == 0
    assert cli("--version").stdout.strip() == "0.2.0"
    assert cli("experiment", "run", "--help").returncode == 0
    assert cli("detect", "--help").returncode == 0


def test_playground_optional_dependency_message(monkeypatch):
    import sys

    import pytest

    from nullmark.cli import CLIError, execute, parser

    monkeypatch.setitem(sys.modules, "nullmark.playground.app", None)
    args = parser().parse_args(["playground"])
    assert args.host == "127.0.0.1" and args.port == 8765
    with pytest.raises(CLIError, match=r"pip install.*nullmark\[gui\]"):
        execute(args)


def test_malformed_yaml_is_reported_without_input_values(tmp_path):
    config = tmp_path / "malformed.yaml"
    config.write_text("seed: [private-input-marker\n")
    failed = cli("generate", "--config", config, "--scheme", "none", "--prompt", "Hello")
    assert failed.returncode == 2
    assert "private-input-marker" not in failed.stdout + failed.stderr
    assert "Traceback" not in failed.stderr


def test_cli_commands_and_errors(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("name: cli_smoke\nrandom_keys: 1\ndataset:\n  sample_count: 1\n")
    output = tmp_path / "run"
    result = cli("experiment", "run", config, "--output", output)
    assert result.returncode == 0, result.stderr
    assert "smoke" in result.stdout
    assert cli("experiment", "summarize", output).returncode == 0
    args = ["--config", config, "--scheme", "kgw", "--secrets", output / "private/secrets.json"]
    generated = cli("generate", *args, "--prompt", "Explain a public library.")
    assert generated.returncode == 0, generated.stderr
    text = tmp_path / "continuation.txt"
    text.write_text(generated.stdout, encoding="utf-8")
    detected = cli("detect", *args, "--text-file", text)
    assert detected.returncode == 0, detected.stderr
    assert json.loads(detected.stdout)["prediction"] is True
    assert json.loads(detected.stdout)["state"] == "INSUFFICIENT EVIDENCE"
    assert json.loads(detected.stdout)["decision_scope"] == "legacy_demo"
    assert (
        cli("generate", "--config", config, "--scheme", "none", "--prompt", "Hello").returncode == 0
    )
    assert (
        cli("generate", "--config", config, "--scheme", "kgw", "--prompt", "Hello").returncode == 2
    )
    bad = tmp_path / "bad.secrets.json"
    bad.write_text('{"master_hex": "secret-should-not-appear"}')
    failed = cli(
        "detect", "--config", config, "--scheme", "kgw", "--secrets", bad, "--text-file", text
    )
    assert failed.returncode == 2
    assert "secret-should-not-appear" not in failed.stdout + failed.stderr
