from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from eventide import EventideRuntime
from storage import get_state_file_path, load_state, save_state


app = FastAPI(
    title="Eventide Service",
    version="0.1.0",
    description="Eventide 身体状态服务",
)

runtime = EventideRuntime()


class TickRequest(BaseModel):
    last_counterpart_message_at: Optional[datetime] = None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@app.get("/")
def root() -> dict:
    return {
        "ok": True,
        "service": "eventide",
        "message": "Eventide service is running",
    }


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "service": "eventide",
        "state_file": get_state_file_path(),
        "time": utc_now().isoformat(),
    }


@app.get("/state")
def get_state() -> dict:
    try:
        state_data = load_state()
        state = runtime.load_state(state_data)

        return {
            "ok": True,
            "state": state_data,
            "body": runtime.payload(state),
            "state_card": runtime.render_card(state, utc_now()),
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"读取状态失败: {error}",
        ) from error


@app.post("/tick")
def tick_state(request: TickRequest) -> dict:
    try:
        now = utc_now()
        state_data = load_state()
        state = runtime.load_state(state_data)

        state_card = runtime.tick_and_render(
            state,
            now,
            last_counterpart_message_at=request.last_counterpart_message_at,
        )

        saved_state = runtime.dump_state(state)
        save_state(saved_state)

        return {
            "ok": True,
            "changed": True,
            "state": saved_state,
            "body": runtime.payload(state),
            "state_card": state_card,
            "time": now.isoformat(),
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"推进状态失败: {error}",
        ) from error
