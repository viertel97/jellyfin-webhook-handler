import os
from quarter_lib.akeyless import get_secrets

API_KEY = get_secrets(["sonarr/api_key"])
SONARR_URL = os.getenv("SONARR_URL", "http://localhost:8989")
