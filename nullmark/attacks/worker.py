"""JSONL stdin/stdout worker; launched with isolated cwd/environment by the supervisor."""

import json
import sys
from dataclasses import asdict

from nullmark.attacks.base import AttackInput
from nullmark.attacks.baselines import BaselineAttack
from nullmark.attacks.skd import METHODS, generate_pool, settings, transform
from nullmark.common.semantic import SemanticSimilarity


def main():
    model = None
    semantic = None
    pools = {}
    try:
        for line in sys.stdin:
            try:
                request = json.loads(line)
                expected = {"sample", "attack", "budget", "seed", "model"}
                if request.get("attack") in METHODS:
                    expected.add("skd")
                if set(request) != expected:
                    raise ValueError("unexpected worker fields")
                sample = AttackInput(**request["sample"])
                if request["model"] and model is None:
                    from nullmark.attacks.model import TransformationModel

                    model = TransformationModel(request["model"])
                if request["attack"] in METHODS:
                    config = settings(request["skd"])
                    if semantic is None:
                        semantic = SemanticSimilarity(
                            cache_folder=request["model"].get("semantic_cache")
                        )
                    identity = json.dumps([asdict(sample), request["seed"], config], sort_keys=True)
                    if identity not in pools:
                        # Cache a failed analysis too; selectors must never regenerate a pool.
                        pools[identity] = None
                        pools[identity] = generate_pool(
                            sample, model, semantic, config, request["seed"]
                        )
                    if pools[identity] is None:
                        raise ValueError("candidate generation previously failed")
                    result = transform(
                        sample,
                        method=request["attack"],
                        k=request["budget"],
                        seed=request["seed"],
                        model=model,
                        artifact=pools[identity],
                    )
                else:
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
