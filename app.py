import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from eventide import EventideRuntime
from storage import get_state_file_path, load_state, save_state


app = FastAPI(
    title="Eventide Service",
    version="0.2.0",
    description="Eventide 身体状态服务",
)

runtime = EventideRuntime()

API_KEY = os.getenv("EVENTIDE_API_KEY", "").strip()

BASE_DIR = Path(__file__).resolve().parent
DASHBOARD_FILE = BASE_DIR / "dashboard.html"


class TickRequest(BaseModel):
    last_counterpart_message_at: Optional[datetime] = None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_datetime(
    value: Optional[datetime],
) -> Optional[datetime]:
    if value is None:
        return None

    if value.tzinfo is None:
        return value.replace(
            tzinfo=timezone.utc
        )

    return value.astimezone(
        timezone.utc
    )


def require_api_key(
    x_api_key: str = Header(
        default="",
        alias="X-API-Key",
    ),
) -> bool:
    if not API_KEY:
        raise HTTPException(
            status_code=503,
            detail="EVENTIDE_API_KEY 尚未配置",
        )

    if not secrets.compare_digest(
        x_api_key,
        API_KEY,
    ):
        raise HTTPException(
            status_code=401,
            detail="访问密钥无效",
        )

    return True


@app.get("/")
def root() -> dict:
    return {
        "ok": True,
        "service": "eventide",
        "message": "Eventide service is running",
        "dashboard": "/dashboard",
    }


@app.get("/dashboard")
def dashboard():
    if not DASHBOARD_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="dashboard.html 不存在",
        )

    return FileResponse(
        path=DASHBOARD_FILE,
        media_type="text/html",
        filename=None,
    )


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "service": "eventide",
        "state_file": get_state_file_path(),
        "dashboard_exists": DASHBOARD_FILE.exists(),
        "time": utc_now().isoformat(),
    }


@app.get("/state")
def get_state(
    authorized: bool = Depends(
        require_api_key
    ),
) -> dict:
    del authorized

    try:
        state_data = load_state()
        state = runtime.load_state(
            state_data
        )

        now = utc_now()

        return {
            "ok": True,
            "state": state_data,
            "body": runtime.payload(
                state
            ),
            "state_card": runtime.render_card(
                state,
                now,
            ),
            "time": now.isoformat(),
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"读取状态失败: {error}",
        ) from error


@app.post("/tick")
def tick_state(
    request: TickRequest,
    authorized: bool = Depends(
        require_api_key
    ),
) -> dict:
    del authorized

    try:
        now = utc_now()

        state_data = load_state()

        state = runtime.load_state(
            state_data
        )

        changed = runtime.tick(
            state,
            now,
            last_counterpart_message_at=
                normalize_datetime(
                    request.last_counterpart_message_at
                ),
        )

        state_card = runtime.render_card(
            state,
            now,
        )

        saved_state = save_state(
            runtime.dump_state(
                state
            )
        )

        return {
            "ok": True,
            "changed": changed,
            "state": saved_state,
            "body": runtime.payload(
                state
            ),
            "state_card": state_card,
            "time": now.isoformat(),
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"推进状态失败: {error}",
        ) from error
