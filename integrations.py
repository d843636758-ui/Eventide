import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


EMOTION_BASE_URL = os.getenv(
    "EMOTION_BASE_URL",
    "https://emotionmcp.zeabur.app",
).rstrip("/")

OB_BASE_URL = os.getenv(
    "OB_BASE_URL",
    "https://webweb.zeabur.app",
).rstrip("/")

OB_HOOK_TOKEN = os.getenv(
    "OB_HOOK_TOKEN",
    "",
).strip()


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
            timeout=15,
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


def fetch_text(
    url: str,
    headers: dict | None = None,
) -> dict:
    request_headers = {
        "Accept": "text/plain",
        "User-Agent": "Eventide-Dashboard",
    }

    if headers:
        request_headers.update(headers)

    request = Request(
        url,
        headers=request_headers,
    )

    try:
        with urlopen(
            request,
            timeout=20,
        ) as response:
            text = response.read().decode(
                "utf-8"
            )

            return {
                "ok": True,
                "text": text,
            }

    except HTTPError as error:
        return {
            "ok": False,
            "text": "",
            "error": f"HTTP {error.code}",
        }

    except URLError as error:
        return {
            "ok": False,
            "text": "",
            "error": str(error.reason),
        }

    except Exception as error:
        return {
            "ok": False,
            "text": "",
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
        "ok": state.get(
            "ok",
            False,
        ),
        "current_mood": state.get(
            "mood"
        ),
        "recent_events": events.get(
            "events",
            [],
        ),
        "error": state.get(
            "error"
        ),
    }


def get_ombre_breath() -> dict:
    if not OB_HOOK_TOKEN:
        return {
            "ok": False,
            "text": "",
            "error": "OB_HOOK_TOKEN 尚未配置",
        }

    return fetch_text(
        f"{OB_BASE_URL}/breath-hook",
        headers={
            "X-Ombre-Hook-Token":
                OB_HOOK_TOKEN,
        },
    )


def get_ombre_dream() -> dict:
    if not OB_HOOK_TOKEN:
        return {
            "ok": False,
            "text": "",
            "error": "OB_HOOK_TOKEN 尚未配置",
        }

    return fetch_text(
        f"{OB_BASE_URL}/dream-hook",
        headers={
            "X-Ombre-Hook-Token":
                OB_HOOK_TOKEN,
        },
    )


def get_ombre_dashboard() -> dict:
    breath = get_ombre_breath()
    dream = get_ombre_dream()

    errors = []

    if not breath.get("ok"):
        errors.append(
            breath.get(
                "error",
                "breath-hook 读取失败",
            )
        )

    if not dream.get("ok"):
        errors.append(
            dream.get(
                "error",
                "dream-hook 读取失败",
            )
        )

    return {
        "ok": (
            breath.get("ok", False)
            or dream.get("ok", False)
        ),
        "memory": breath.get(
            "text",
            "",
        ),
        "dream": dream.get(
            "text",
            "",
        ),
        "errors": errors,
    }
