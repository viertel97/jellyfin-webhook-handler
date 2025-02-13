import os
from quarter_lib.akeyless import get_secrets

SONAR_API_KEY, JELLYFIN_API_KEY = get_secrets(["sonarr/api_key", "jellyfin/api_key"])
SONARR_URL = os.getenv("SONARR_URL", "http://localhost:8989")
JELLYFIN_URL = os.getenv("JELLYFIN_URL", "http://localhost:8096")
