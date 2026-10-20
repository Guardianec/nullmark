"""Small standard-library CLI; detector commands belong to the trusted evaluator."""

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError
from yaml import YAMLError

from nullmark import __version__
from nullmark.config import load_config
from nullmark.evaluation.metrics import summary_markdown


class CLIError(ValueError):
    """A user-facing validation message constructed without private input values."""


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="nullmark", description="Open text-watermark reproducibility"
    )
    root.add_argument("--version", action="version", version=__version__)
    commands = root.add_subparsers(dest="command", required=True)
    calibrate = commands.add_parser("calibrate", help="Calibrate frozen detector operating points")
    calibrate.add_argument("config", type=Path)
    calibrate.add_argument("--output", type=Path)
    calibrate.add_argument("--secrets", type=Path, help="Replay using a private calibration master")
    playground = commands.add_parser("playground", help="Launch the local Visual Playground")
    playground.add_argument("--host", choices=("127.0.0.1", "localhost"), default="127.0.0.1")
    playground.add_argument("--port", type=int, default=8765)
    playground.add_argument("--calibration", type=Path, action="append", default=[])
    playground.add_argument("--secrets", type=Path, help="Private master matching loaded artifacts")
    model = commands.add_parser("model", help="Check an installed local inference backend")
    model_commands = model.add_subparsers(dest="model_command", required=True)
    check = model_commands.add_parser(
        "check-ollama", help="Verify GGUF logits and watermark capability"
    )
    check.add_argument("name", help="Exact installed Ollama model name; never pulls weights")
    check.add_argument("--offload", choices=("auto", "cpu", "gpu"), default="auto")
    check.add_argument("--tokens", type=int, default=128)
    for command in ("generate", "detect"):
        sub = commands.add_parser(command, help=f"{command.capitalize()} a local controlled sample")
        sub.add_argument("--config", type=Path, required=True)
        sub.add_argument(
            "--scheme",
            choices=("none", "synthid", "kgw") if command == "generate" else ("synthid", "kgw"),
            required=True,
        )
        sub.add_argument(
            "--secrets", type=Path, help="Private master file (required for watermarking)"
        )
        sub.add_argument("--key-index", type=int, default=0)
        if command == "generate":
            sub.add_argument("--prompt", required=True)
            sub.add_argument("--seed", type=int, default=42)
        else:
            sub.add_argument(
                "--text-file", type=Path, required=True, help="UTF-8 continuation only"
            )
    experiment = commands.add_parser("experiment", help="Run or summarize an experiment")
    exp_commands = experiment.add_subparsers(dest="experiment_command", required=True)
    run = exp_commands.add_parser("run", help="Generate both families and paired plain controls")
    run.add_argument("config", type=Path)
    run.add_argument("--output", type=Path, help="New output directory; existing paths are refused")
    run.add_argument(
        "--secrets", type=Path, help="Replay with a previous run's private master file"
    )
    summary = exp_commands.add_parser("summarize", help="Print stored descriptive metrics")
    summary.add_argument("result", type=Path, help="Run directory or metrics.json")
    return root


def execute(args) -> int:
    if args.command == "calibrate":
        from nullmark.experiments.calibration import run_calibration

        output = run_calibration(args.config, output=args.output, secrets_path=args.secrets)
        print((output / "summary.md").read_text("utf-8"))
        print(f"Results: {output.resolve()}")
        return 0
    if args.command == "model":
        from nullmark.models.diagnostics import check_ollama
        from nullmark.models.ollama import LocalModelError

        try:
            report = check_ollama(args.name, offload=args.offload, tokens=args.tokens)
        except LocalModelError as exc:
            raise CLIError(str(exc)) from None
        print(json.dumps(report, indent=2, allow_nan=False))
        return int(not report["passed"])
    if args.command == "playground":
        if not 1 <= args.port <= 65535:
            raise CLIError("port must be between 1 and 65535")
        try:
            from nullmark.playground.app import launch
        except ImportError:
            raise CLIError(
                "The Visual Playground requires optional GUI dependencies. "
                'Install with: pip install "nullmark[gui]" (checkout: pip install -e ".[gui]")'
            ) from None
        print(f"NullMark Visual Playground: http://{args.host}:{args.port}", flush=True)
        from nullmark.evaluation.calibration import CalibratedDetector
        from nullmark.evaluation.secrets import KeyStore

        if args.calibration and args.secrets is None:
            raise CLIError("--calibration requires its matching --secrets private master file")
        launch(
            args.host,
            args.port,
            keys=KeyStore.load(args.secrets) if args.secrets else None,
            calibrations=[CalibratedDetector.load(p) for p in args.calibration],
        )
        return 0
    if args.command == "experiment":
        if args.experiment_command == "summarize":
            path = args.result / "metrics.json" if args.result.is_dir() else args.result
            metrics = json.loads(path.read_text("utf-8"))
            print(summary_markdown(metrics, metrics["purpose"]))
            return 0
        from nullmark.experiments.runner import run_experiment

        output = run_experiment(args.config, output=args.output, secrets_path=args.secrets)
        metrics = json.loads((output / "metrics.json").read_text("utf-8"))
        print(summary_markdown(metrics, metrics["purpose"]))
        print(f"Results: {output.resolve()}")
        return int(bool(metrics["generation_failures"] or metrics["detection_failures"]))
    if args.key_index < 0:
        raise CLIError("key-index must be nonnegative")
    config = load_config(args.config)
    if args.command == "generate" and not 0 <= args.seed < 2**32:
        raise CLIError("seed must be in [0, 2**32)")
    if args.scheme != "none" and args.secrets is None:
        raise CLIError(
            "--secrets is required; run a tiny experiment to create a private master file"
        )
    from nullmark.evaluation.secrets import KeyStore
    from nullmark.models import load_model
    from nullmark.watermark.registry import load_scheme

    model = load_model(config.model)
    scheme = None
    if args.scheme != "none":
        store = KeyStore.load(args.secrets)
        scheme = load_scheme(
            args.scheme,
            model,
            config,
            store.derive(args.scheme, args.key_index, config.synthid.depth),
        )
    if args.command == "generate":
        generated = (
            scheme.generate(model, args.prompt, seed=args.seed)
            if scheme
            else model.generate(args.prompt, seed=args.seed)
        )
        sys.stdout.write(generated.text)
    else:
        detected = scheme.detect(args.text_file.read_text("utf-8"))
        print(
            json.dumps(
                {
                    **detected.to_dict(),
                    "state": detected.state,
                    "classification_note": "prediction is legacy/demo only; use a frozen "
                    "calibrated evaluator for research decisions",
                },
                allow_nan=False,
            )
        )
    model.close()
    return 0


def main() -> None:
    # Redirected artifacts must remain UTF-8 on Windows as well as Unix.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    args = parser().parse_args()
    try:
        code = execute(args)
    except CLIError as exc:
        print(f"nullmark: {exc}", file=sys.stderr)
        code = 2
    except ValidationError as exc:
        # Pydantic normally includes input values, including secrets in a malformed private file.
        locations = [
            ".".join(map(str, e["loc"])) or "root" for e in exc.errors(include_input=False)
        ]
        print(f"nullmark: invalid configuration at {', '.join(locations)}", file=sys.stderr)
        code = 2
    except (OSError, ValueError, RuntimeError, KeyError, YAMLError) as exc:
        # Upstream exceptions may embed private config. Keep terminal errors non-secret.
        message = str(exc) if isinstance(exc, FileExistsError) else type(exc).__name__
        print(
            f"nullmark: {message}. Check paths/configuration and model availability.",
            file=sys.stderr,
        )
        code = 2
    raise SystemExit(code)
