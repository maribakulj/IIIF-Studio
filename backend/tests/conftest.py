# Re-export des fixtures partagées pour la découverte automatique par pytest.
# Le fichier conftest_api.py contient les vraies définitions (async_client, etc.).
from tests.conftest_api import *  # noqa: F401, F403
