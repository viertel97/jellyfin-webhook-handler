import requests
from quarter_lib.logging import setup_logging


from config.configuration import JELLYFIN_URL, JELLYFIN_API_KEY

logger = setup_logging(__file__)

def update_jellyfin_library():
    url = f"{JELLYFIN_URL}/ScheduledTasks/Running/7738148ffcd07979c7ceb148e06b3aed"
    headers = {"Authorization": f'MediaBrowser Token="{JELLYFIN_API_KEY}"'}
    response = requests.post(url, headers=headers)
    if response.status_code != 200:
        logger.error(f"Error updating Jellyfin library: {response.content}")
        return
    logger.info("Jellyfin library update successful")