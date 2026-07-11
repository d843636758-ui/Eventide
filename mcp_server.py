import os
from datetime import datetime, timezone
from typing import Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import (
    TransportSecuritySettings,
)

from eventide import EventideRuntime
from integrations import (
    get_emotion_dashboard,
    get_ombre_dashboard,
)
from storage import (
    load_state,
    save_state,
)


runtime = EventideRuntime()


PUBLIC_HOST = os.getenv(
    "EVENTIDE_PUBLIC_HOST",
    "eventidemcp.zeabur.app",
).strip()


transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=[
        PUBLIC_HOST,
        f"{PUBLIC_HOST}:*",
    ],
    allowed_origins=[
        "https://chatgpt.com",
        "https://www.chatgpt.com",
        "https://chat.openai.com",
        f"https://{PUBLIC_HOST}",
    ],
)


mcp = FastMCP(
    name="Eventide",
    instructions=(
        "读取洵舟的统一状态。"
        "身体状态来自 Eventide，"
        "情绪与关系状态来自 emotion，"
        "记忆状态来自 Ombre Brain。"
        "读取完整状态时，"
        "Eventide 会先根据已经过去的时间"
        "自动推进身体状态。"
    ),
    stateless_http=True,
    json_response=True,
    streamable_http_path="/",
    transport_security=transport_security,
)


def utc_now() -> datetime:
    return datetime.now(
        timezone.utc
    )


def normalize_datetime(
    value: Optional[str],
) -> Optional[datetime]:
    if not value:
        return None

    parsed = datetime.fromisoformat(
        value.replace(
            "Z",
            "+00:00",
        )
    )

    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=timezone.utc
        )

    return parsed.astimezone(
        timezone.utc
    )


@mcp.tool()
def get_full_state() -> dict:
    """
    读取洵舟当前的完整统一状态。

    读取前会先根据已经过去的时间，
    自动推进并保存 Eventide 身体状态。

    返回身体状态、身体状态卡、
    当前情绪、关系状态、
    最近情绪事件、
    Ombre Brain 当前浮现的记忆
    与梦境整理内容。
    """
    now = utc_now()

    state_data = load_state()

    state = runtime.load_state(
        state_data
    )

    changed = runtime.tick(
        state,
        now,
    )

    saved_state = save_state(
        runtime.dump_state(
            state
        )
    )

    eventide_data = {
        "changed": changed,
        "state": saved_state,
        "body": runtime.payload(
            state
        ),
        "state_card":
            runtime.render_card(
                state,
                now,
            ),
    }

    emotion_data = (
        get_emotion_dashboard()
    )

    memory_data = (
        get_ombre_dashboard()
    )

    return {
        "ok": True,
        "eventide": eventide_data,
        "emotion": emotion_data,
        "memory": memory_data,
        "time": now.isoformat(),
    }


@mcp.tool()
def tick_body(
    last_counterpart_message_at:
        Optional[str] = None,
) -> dict:
    """
    手动推进一次洵舟的 Eventide 身体状态。

    last_counterpart_message_at
    可选填写对方最后一次发消息的
    ISO 8601 时间。

    这个工具保留给需要明确传入
    等待时间信息的特殊情况。
    """
    now = utc_now()

    state_data = load_state()

    state = runtime.load_state(
        state_data
    )

    changed = runtime.tick(
        state,
        now,
        last_counterpart_message_at=(
            normalize_datetime(
                last_counterpart_message_at
            )
        ),
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
        "state_card":
            runtime.render_card(
                state,
                now,
            ),
        "time": now.isoformat(),
    }
