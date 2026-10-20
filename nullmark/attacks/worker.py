"""JSONL stdin/stdout worker; launched with isolated cwd/environment by the supervisor."""

import json
import sys
from dataclasses import asdict

from nullmark.attacks.base import AttackInput
from nullmark.attacks.baselines import BaselineAttack


def main():
    model = None
    try:
        for line in sys.stdin:
            try:
                request = json.loads(line)
                if set(request) != {"sample", "attack", "budget", "seed", "model"}:
                    raise ValueError("unexpected worker fields")
                sample = AttackInput(**request["sample"])
                if request["model"] and model is None:
                    from nullmark.attacks.model import TransformationModel

                    model = TransformationModel(request["model"])
                result = BaselineAttack(
                    request["attack"],
                    request["budget"],
                    model if request["attack"] != "random_edit" else None,
                ).transform(sample, seed=request["seed"])
                response = {"output": asdict(result)}
            except Exception as exc:
                response = {"failure": type(exc).__name__}
            print(json.dumps(response, allow_nan=False), flush=True)
    finally:
        if model:
            model.close()


if __name__ == "__main__":
    main()
