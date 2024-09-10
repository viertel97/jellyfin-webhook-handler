import json

from proxies.telegram_proxy import log_to_telegram
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from quarter_lib.logging import setup_logging

from services.sonarr_service import get_series_by_name, get_episodes, get_next_episodes, add_monitoring_for_episodes, \
    refresh_series, get_current_episode_index, get_episodes_to_delete, delete_episodes

logger = setup_logging(__file__)

app = FastAPI()


@app.post("/webhook")
async def webhook(request: Request):
    try:
        raw_data = await request.body()

        data_str = raw_data.decode('utf-8')
        logger.info("Decoded Data:", data_str)

        data = json.loads(data_str)
        logger.info("Parsed JSON:", data)

    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    title = data["SeriesName"]
    season = int(data["SeasonNumber"])
    episode = int(data["EpisodeNumber"])
    matched_series = get_series_by_name(title)
    if matched_series:
        series_id = matched_series["id"]
        episodes = get_episodes(series_id)
        current_episode_index = get_current_episode_index(episode, season, episodes)
        next_episodes, next_episodes_log = get_next_episodes(episodes=episodes, current_season=season, current_episode=episode, current_episode_index=current_episode_index)
        if next_episodes:
            add_result = add_monitoring_for_episodes(next_episodes)
            logger.info(add_result)
            refresh_result = refresh_series(series_id)
            logger.info(refresh_result)
            log_to_telegram(f"Added monitoring for next episodes {next_episodes_log} for {title} starting from S{season}E{episode}", logger)
            #return JSONResponse(content={"status": "received"}, status_code=200)
        else:
            log_to_telegram(f"Could not find next episode for {title} S{season}E{episode}", logger)
            #return JSONResponse(content={"status": "Next episode not found"}, status_code=204)
        # delete last episodes
        episodes_to_delete = get_episodes_to_delete(episodes=episodes, distance_from_current_episode=2, current_episode_index=current_episode_index, number_of_episodes=3)
        delete_episodes(episodes_to_delete)




    else:
        log_to_telegram(f"Could not find series with title {title}", logger)
        return JSONResponse(content={"status": "Series not found"}, status_code=204)


# health check
@app.get("/health")
def read_root():
    return {"status": "ok"}



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80)
