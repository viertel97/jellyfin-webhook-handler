import requests
from expiringdict import ExpiringDict
from quarter_lib.logging import setup_logging
from rapidfuzz import fuzz, process
from slugify import slugify

from config.configuration import SONARR_URL, API_KEY
from proxies.telegram_proxy import log_to_telegram

logger = setup_logging(__file__)

lookup_endpoint = f"{SONARR_URL}/api/v3/series"
episode_endpoint = f"{SONARR_URL}/api/v3/episode"
monitor_endpoint = f"{SONARR_URL}/api/v3/episode/monitor"
episodeFile_endpoint = f"{SONARR_URL}/api/v3/episodefile"

HEADERS = {"X-Api-Key": API_KEY}
CACHE = ExpiringDict(max_len=100, max_age_seconds=10)


def get_series():
    if CACHE.get("series"):
        return CACHE.get("series")
    response = requests.get(lookup_endpoint, headers=HEADERS)
    if response.status_code != 200:
        logger.error(f"Error getting series: {response.content}")
        return
    response_json = response.json()
    CACHE["series"] = response_json
    return response_json


def get_episodes(series_id: int):
    payload = {"seriesId": series_id}
    response = requests.get(episode_endpoint, headers=HEADERS, params=payload)
    episodes = response.json()
    return sorted(episodes, key=lambda x: (x['seasonNumber'], x['episodeNumber']))


def find_best_match(query, series_data, threshold=80):
    query_slug = slugify(query)
    logger.info(f"Finding best match for {query} ({query_slug})")

    slugs = [item["titleSlug"] for item in series_data]
    titles = [item["title"] for item in series_data]

    slug_match = process.extractOne(query_slug, slugs, scorer=fuzz.ratio)

    if slug_match and slug_match[1] >= threshold:
        matched_item = series_data[slug_match[2]]
        return matched_item, slug_match[1]

    title_match = process.extractOne(query, titles, scorer=fuzz.ratio)

    if title_match and title_match[1] >= threshold:
        matched_item = series_data[title_match[2]]
        return matched_item, title_match[1]

    return None, 0


def get_series_by_name(series_name: str):
    series_data = get_series()
    matched_item, score = find_best_match(series_name, series_data)
    if matched_item:
        return matched_item
    logger.error(f"Could not find series with name {series_name}")
    return None


def get_next_episodes(episodes, current_season: int, current_episode: int, current_episode_index: int,
                      number_of_episodes=2):
    if current_episode_index is None:
        logger.error(f"Could not find episode with season {current_season} and episode {current_episode}")
        return None, None
    start_index = current_episode_index + number_of_episodes - 1
    end_index = current_episode_index + number_of_episodes + 1
    next_two_episodes = episodes[start_index:end_index]
    if not next_two_episodes:
        log_to_telegram(f"Could not find next episodes for season {current_season} and episode {current_episode}",
                        logger)
        return None, None
    next_two_episodes = [episode for episode in next_two_episodes if not episode["hasFile"]]
    if not next_two_episodes:
        log_to_telegram(f"No episodes without files found after season {current_season} and episode {current_episode}",
                        logger)
        return None, None
    next_episodes_log = [{"seasonNumber": episode["seasonNumber"], "episodeNumber": episode["episodeNumber"]} for
                         episode in next_two_episodes]
    logger.info(
        f"Current season: {current_season}, current episode: {current_episode} - Next two episodes: {next_episodes_log}")
    return next_two_episodes, next_episodes_log


def get_last_episodes(episodes, current_episode_index: int,
                      number_of_episodes=2):
    if current_episode_index is None:
        return None
    last_episodes = episodes[current_episode_index - number_of_episodes:current_episode_index]
    if not last_episodes:
        return None
    return last_episodes


def delete_episodes(episodes):
    episodes = [episode for episode in episodes if episode["hasFile"]]
    if not episodes:
        return
    for episode in episodes:
        response = requests.delete(f"{episodeFile_endpoint}/{episode['episodeFileId']}", headers=HEADERS)
        log_to_telegram(f"Deleted episode: {episode['id']} - {episode['title']} with response: {response.content}",
                        logger)


def get_current_episode_index(current_episode, current_season, episodes):
    current_index = None
    for i, ep in enumerate(episodes):
        if ep['seasonNumber'] == int(current_season) and ep['episodeNumber'] == int(current_episode):
            current_index = i
            break
    return int(current_index)


def add_monitoring_for_episodes(episodes):
    ids = [episode["id"] for episode in episodes]
    payload = {"episodeIds": ids, "monitored": True}
    response = requests.put(monitor_endpoint, headers=HEADERS, json=payload)
    logger.info(f"Response: {response.content}")
    return response.json()


def refresh_series(series_id: int):
    refresh_endpoint = f"{SONARR_URL}/api/v3/command"
    payload = {"name": "SeriesSearch", "seriesId": series_id}
    response = requests.post(refresh_endpoint, headers=HEADERS, json=payload)
    return response.json()
