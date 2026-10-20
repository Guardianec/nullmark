import pytest

from nullmark.config import ExperimentConfig
from nullmark.evaluation.secrets import KeyStore
from nullmark.models import CausalModel


@pytest.fixture(scope="session")
def config():
    return ExperimentConfig()


@pytest.fixture(scope="session")
def model(config):
    return CausalModel(config.model)


@pytest.fixture
def keys():
    return KeyStore(bytes(range(32)))
