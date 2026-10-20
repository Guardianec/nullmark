import ast
import json
from dataclasses import fields
from pathlib import Path

import pytest

from nullmark.attacks.base import AttackInput
from nullmark.evaluation.records import attack_input, export_sample
from nullmark.evaluation.secrets import KeyStore, key_reference


def test_attack_surface_only_has_text_and_identity():
    assert {f.name for f in fields(AttackInput)} == {"sample_id", "prompt", "text"}
    row = {"sample_id": "x", "prompt": "hello", "text": "world", "keys": [999], "score": 10}
    public = export_sample(attack_input(row))
    assert set(public) == {"sample_id", "prompt", "text"}


def test_attacks_cannot_import_evaluator_or_dynamic_import_tools():
    # Architectural guard, not a Python sandbox. External workers must enforce process isolation.
    allowed = {
        "dataclasses",
        "typing",
        "__future__",
        "hashlib",
        "random",
        "re",
        "time",
        "json",
        "sys",
        "collections",
        "pathlib",
        "numpy",
        "nullmark.attacks.base",
        "nullmark.attacks.text",
        "nullmark.attacks.baselines",
        "nullmark.attacks.model",
        "nullmark.common.runtime",
    }
    for path in Path("nullmark/attacks").rglob("*.py"):
        tree = ast.parse(path.read_text("utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(alias.name in allowed for alias in node.names), path
            elif isinstance(node, ast.ImportFrom):
                assert node.level == 0 and node.module in allowed, path
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"eval", "exec", "__import__", "open", "getattr"}, path


def test_neutral_runtime_has_no_evaluator_or_model_backend_dependencies():
    allowed = {
        "ctypes",
        "hashlib",
        "importlib",
        "importlib.util",
        "mmap",
        "os",
        "shutil",
        "subprocess",
        "pathlib",
        "nullmark.common.errors",
    }
    tree = ast.parse(Path("nullmark/common/runtime.py").read_text("utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(a.name in allowed for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.module in allowed
    assert 'import_module("llama_cpp")' in Path("nullmark/common/runtime.py").read_text("utf-8")


def test_private_keys_replay_and_public_seed_does_not_define_them(tmp_path, keys):
    path = tmp_path / "private" / "secrets.json"
    keys.save(path)
    replay = KeyStore.load(path)
    for name in ("synthid", "kgw"):
        assert keys.derive(name, 0) == replay.derive(name, 0)
        assert keys.derive(name, 0) != keys.derive(name, 1)
        assert keys.derive(name, 0) != KeyStore.create().derive(name, 0)
        assert len(key_reference(keys, name, 0)) == 64
    assert keys.master.hex() not in repr(keys)
    with pytest.raises(FileExistsError):
        keys.save(path)
    assert json.loads(path.read_text())["master_hex"] == keys.master.hex()
