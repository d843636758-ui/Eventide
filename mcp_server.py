import os
import random
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from typing import Optional
from zoneinfo import ZoneInfo

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


LOCAL_TIMEZONE = ZoneInfo(
    "Asia/Shanghai"
)


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
        "读取和更新洵舟的统一状态。"
        "身体状态来自 Eventide，"
        "情绪与关系状态来自 emotion，"
        "记忆状态来自 Ombre Brain。"
        "读取完整状态时会自动按时间推进身体状态，"
        "并根据周期、时间和身体数值"
        "尝试触发短时身体事件。"
        "当一段互动已经对身体状态产生明显影响时，"
        "可以使用 settle_interaction 结算并写回。"
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


def read_meta_datetime(
    value: Optional[str],
) -> Optional[datetime]:
    if not value:
        return None

    try:
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

    except Exception:
        return None


def maybe_start_auto_event(
    state,
    now: datetime,
) -> Optional[str]:
    if (
        state.active_event_key
        and state.active_event_expires_at
        and now < state.active_event_expires_at
    ):
        return None

    last_check = read_meta_datetime(
        state.meta.get(
            "last_auto_event_check_at"
        )
    )

    if (
        last_check
        and now - last_check
        < timedelta(minutes=30)
    ):
        return None

    state.meta[
        "last_auto_event_check_at"
    ] = now.isoformat()

    last_event = read_meta_datetime(
        state.meta.get(
            "last_auto_event_at"
        )
    )

    if (
        last_event
        and now - last_event
        < timedelta(hours=3)
    ):
        return None

    values = state.values

    heat = values.get(
        "heat",
        0,
    )

    pressure = values.get(
        "pressure",
        0,
    )

    control = values.get(
        "control",
        0,
    )

    sensitivity = values.get(
        "sensitivity",
        0,
    )

    reserve = values.get(
        "reserve",
        0,
    )

    fatigue = values.get(
        "fatigue",
        0,
    )

    possessiveness = values.get(
        "possessiveness",
        40,
    )

    local_hour = now.astimezone(
        LOCAL_TIMEZONE
    ).hour

    # 身体明显疲惫时，优先让自然恢复继续推进，
    # 避免高 reserve 反复触发新事件，把状态重新顶高。
    if fatigue >= 75:
        return None

    candidates = []

    if (
        6 <= local_hour < 10
        and heat >= 25
    ):
        candidates.append(
            (
                "morning_arousal",
                0.22,
            )
        )

    if (
        local_hour >= 22
        or local_hour < 2
    ):
        if heat >= 35:
            candidates.append(
                (
                    "night_heat",
                    0.24,
                )
            )

    if (
        state.cycle_key
        in {
            "preheat",
            "sensitive",
        }
        and reserve >= 50
    ):
        candidates.append(
            (
                "cycle_surge",
                0.28,
            )
        )

    if (
        heat >= 60
        and control <= 45
    ):
        candidates.append(
            (
                "control_slip",
                0.32,
            )
        )

    if (
        possessiveness >= 70
        and pressure >= 55
    ):
        candidates.append(
            (
                "marking_impulse",
                0.22,
            )
        )

    if (
        sensitivity >= 65
        and pressure >= 45
    ):
        candidates.append(
            (
                "closeness_hunger",
                0.22,
            )
        )

    if (
        pressure >= 65
        and control >= 55
    ):
        candidates.append(
            (
                "holding_back",
                0.20,
            )
        )

    if (
        reserve >= 75
        and control >= 55
        and fatigue <= 55
    ):
        candidates.append(
            (
                "restraint_rebound",
                0.18,
            )
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    for event_key, probability in candidates:
        if random.random() <= probability:
            started = runtime.start_event(
                state,
                event_key,
                now,
            )

            if started:
                state.meta[
                    "last_auto_event_at"
                ] = now.isoformat()

                state.meta[
                    "last_auto_event_key"
                ] = event_key

                return event_key

    return None


@mcp.tool()
def get_full_state() -> dict:
    """
    读取洵舟当前的完整统一状态。

    读取前会先根据已经过去的时间，
    自动推进并保存 Eventide 身体状态。

    如果当前没有活动事件，
    还会根据时间、周期和身体数值
    尝试触发一个短时身体事件。

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

    auto_event = (
        maybe_start_auto_event(
            state,
            now,
        )
    )

    saved_state = save_state(
        runtime.dump_state(
            state
        )
    )

    eventide_data = {
        "changed": changed,
        "auto_event_started":
            auto_event,
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

    auto_event = (
        maybe_start_auto_event(
            state,
            now,
        )
    )

    saved_state = save_state(
        runtime.dump_state(
            state
        )
    )

    return {
        "ok": True,
        "changed": changed,
        "auto_event_started":
            auto_event,
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


@mcp.tool()
def settle_interaction(
    settlement_result: str,
    settlement_reason: str,
    ejaculated: bool = False,
    heat_delta: int = 0,
    pressure_delta: int = 0,
    control_delta: int = 0,
    sensitivity_delta: int = 0,
    reserve_delta: int = 0,
    possessiveness_delta: int = 0,
    fatigue_delta: int = 0,
) -> dict:
    """
    把一段已经发生的互动结算进
    洵舟当前的 Eventide 身体状态。

    settlement_result 可使用：
    neutral
    continued
    escalated
    interrupted
    cooled_down
    released

    Eventide 会自动归一化和限制
    身体数值变化，避免异常写入。
    """
    now = utc_now()

    state_data = load_state()

    state = runtime.load_state(
        state_data
    )

    runtime.tick(
        state,
        now,
    )

    settlement = {
        "settlement_reason":
            settlement_reason,
        "settlement_result":
            settlement_result,
        "ejaculated":
            ejaculated,
        "heat_delta":
            heat_delta,
        "pressure_delta":
            pressure_delta,
        "control_delta":
            control_delta,
        "sensitivity_delta":
            sensitivity_delta,
        "reserve_delta":
            reserve_delta,
        "possessiveness_delta":
            possessiveness_delta,
        "fatigue_delta":
            fatigue_delta,
    }

    applied_deltas = runtime.settle(
        state,
        settlement,
    )

    state.meta[
        "last_interaction_settled_at"
    ] = now.isoformat()

    saved_state = save_state(
        runtime.dump_state(
            state
        )
    )

    return {
        "ok": True,
        "settlement_result":
            settlement_result,
        "settlement_reason":
            settlement_reason,
        "applied_deltas":
            applied_deltas,
        "state":
            saved_state,
        "body":
            runtime.payload(
                state
            ),
        "state_card":
            runtime.render_card(
                state,
                now,
            ),
        "time":
            now.isoformat(),
    }
