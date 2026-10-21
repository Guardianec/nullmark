"""Trusted supervisor: explicit public allowlist, clean cwd/env and immutable cache."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

from nullmark.attacks.base import AttackOutput
from nullmark.attacks.baselines import TEMPLATE, VERSION, validate_output
from nullmark.attacks.skd import METHODS, SKDOutput, settings
from nullmark.attacks.skd import VERSION as SKD_VERSION
from nullmark.evaluation.records import export_sample


def cache_identity(request):
    # Paths are operational; model content, sample and all settings define identity.
    value = json.loads(json.dumps(request))
    if value["model"]:
        value["model"].pop("model_path", None)
    return hashlib.sha256(
        json.dumps(
            {
                "request": value,
                "version": SKD_VERSION if value["attack"] in METHODS else VERSION,
                "template": SKD_VERSION if value["attack"] in METHODS else TEMPLATE,
            },
            sort_keys=True,
            allow_nan=False,
        ).encode()
    ).hexdigest()


class AttackWorker:
    def __init__(self, *, model=None, cache=None, timeout=600):
        self.model, self.cache, self.timeout = model, cache, timeout
        self.process = None
        self.directory = None

    def _kill(self):
        # Windows venv launchers can own a second Python process holding the pipes.
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(self.process.pid), "/T", "/F"],
                capture_output=True,
                check=False,
                timeout=15,
            )
        else:
            self.process.kill()

    def _start(self):
        self.directory = tempfile.TemporaryDirectory(prefix="nullmark-attack-")
        env = {
            k: os.environ[k]
            for k in (
                "SYSTEMROOT",
                "WINDIR",
                "PATH",
                "TEMP",
                "TMP",
                "USERPROFILE",
                "LOCALAPPDATA",
            )
            if k in os.environ
        }
        # -I ignores PYTHONPATH, user site and inherited Python configuration.
        # Source checkout path is fixed by the supervisor, never supplied by a sample.
        package_root = str(Path(__file__).resolve().parents[2])
        bootstrap = (
            f"import sys; sys.path.insert(0, {package_root!r}); "
            "from nullmark.attacks.worker import main; main()"
        )
        self.stderr = tempfile.TemporaryFile()
        self.process = subprocess.Popen(
            [sys.executable, "-I", "-u", "-c", bootstrap],
            cwd=self.directory.name,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.stderr,
            text=True,
            encoding="utf-8",
        )

    def transform(self, sample, *, attack, budget, seed, skd=None):
        request = {
            "sample": export_sample(sample),
            "attack": attack,
            "budget": budget,
            "seed": seed,
            "model": self.model if attack != "random_edit" else None,
        }
        output_type = SKDOutput if attack in METHODS else AttackOutput
        if attack in METHODS:
            request["skd"] = settings(skd)
        identity = cache_identity(request)
        path = self.cache / f"{identity}.json" if self.cache else None
        if path and path.exists():
            stored = json.loads(path.read_text("utf-8"))
            if stored["identity"] != identity:
                raise ValueError("attack cache identity mismatch")
            serialized = json.dumps(stored["output"], sort_keys=True, allow_nan=False).encode()
            if hashlib.sha256(serialized).hexdigest() != stored["output_sha256"]:
                raise ValueError("attack cache content mismatch")
            result = output_type(**stored["output"])
            validate_output(sample.text, result.text, sample.prompt)
            return result
        if self.process is not None and self.process.poll() is not None:
            self.close()
        if self.process is None:
            self._start()
        from concurrent.futures import ThreadPoolExecutor, TimeoutError

        self.process.stdin.write(json.dumps(request, allow_nan=False) + "\n")
        self.process.stdin.flush()
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(self.process.stdout.readline)
            try:
                line = pending.result(timeout=self.timeout)
            except TimeoutError:
                self._kill()
                raise RuntimeError("attack worker timeout") from None
        response = json.loads(line)
        if "failure" in response:
            raise RuntimeError("attack transformation failed: " + response["failure"])
        result = output_type(**response["output"])
        validate_output(sample.text, result.text, sample.prompt)
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8") as handle:
                content = asdict(result)
                checksum = hashlib.sha256(
                    json.dumps(content, sort_keys=True, allow_nan=False).encode()
                ).hexdigest()
                json.dump(
                    {"identity": identity, "output": content, "output_sha256": checksum},
                    handle,
                    allow_nan=False,
                )
        return result

    def close(self):
        if self.process:
            self.process.stdin.close()
            try:
                self.process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self._kill()
                self.process.wait()
            self.process.stdout.close()
            self.stderr.close()
            self.process = None
        if self.directory:
            self.directory.cleanup()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
