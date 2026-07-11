import json
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


EMOTION_BASE_URL = "https://emotionmcp.zeabur.app"


def fetch_json(url: str) -> dict:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "Eventide-Dashboard",
        },
    )

    try:
        with urlopen(
            request,
            timeout=10,
        ) as response:
            data = response.read().decode(
                "utf-8"
            )

            return json.loads(data)

    except HTTPError as error:
        return {
            "ok": False,
            "error": f"HTTP {error.code}",
        }

    except URLError as error:
        return {
            "ok": False,
            "error": str(error.reason),
        }

    except Exception as error:
        return {
            "ok": False,
            "error": str(error),
        }


def get_emotion_state() -> dict:
    data = fetch_json(
        f"{EMOTION_BASE_URL}/mood"
    )

    if data.get("ok") is False:
        return data

    return {
        "ok": True,
        "mood": data,
    }


def get_emotion_events() -> dict:
    data = fetch_json(
        f"{EMOTION_BASE_URL}/mood/events"
    )

    if isinstance(data, list):
        return {
            "ok": True,
            "events": data[-20:][::-1],
        }

    return {
        "ok": False,
        "events": [],
        "error": "情绪事件格式异常",
    }


def get_emotion_dashboard() -> dict:
    state = get_emotion_state()
    events = get_emotion_events()

    return {
        "ok": state.get("ok", False),
        "current_mood": state.get(
            "mood"
        ),
        "recent_events": events.get(
            "events",
            [],
        ),
        "error": state.get("error"),
    }
