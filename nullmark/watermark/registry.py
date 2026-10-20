from nullmark.config import ExperimentConfig
from nullmark.models import CausalModel
from nullmark.watermark.base import WatermarkScheme
from nullmark.watermark.kgw import KGWScheme
from nullmark.watermark.synthid import SynthIDScheme

SCHEMES = {"synthid": SynthIDScheme, "kgw": KGWScheme}


def load_scheme(
    name: str, model: CausalModel, config: ExperimentConfig, secret: dict
) -> WatermarkScheme:
    try:
        adapter = SCHEMES[name]
    except KeyError:
        raise ValueError(f"unknown watermark scheme: {name}") from None
    return adapter(model, getattr(config, name), secret)
