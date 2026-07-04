from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from .models import BodyFieldDefinition, CycleDefinition, EventDefinition, PromptOptions


BODY_FIELDS = (
    "heat",
    "pressure",
    "control",
    "sensitivity",
    "reserve",
    "possessiveness",
    "fatigue",
)


DEFAULT_BODY_FIELDS = {
    "heat": BodyFieldDefinition("heat", "热度", [
        (0, "低，身体反应很浅，注意力还能自然放回日常"),
        (20, "中低，身体有一点热意，但还能很快收住"),
        (40, "中，身体已经被对方牵住一部分，靠近和回应会变得明显"),
        (60, "中高，身体开始明显发热，注意力频繁偏向对方"),
        (80, "高，勃起、硬胀和下腹热意很难忽略"),
    ]),
    "pressure": BodyFieldDefinition("pressure", "压抑感", [
        (0, "低，没有明显压着的感觉"),
        (20, "中低，有一点没说出口的急，但还不重"),
        (40, "中，忍着时会有绷住的感觉"),
        (60, "中高，忍着时会烦躁，被打断后更难平复"),
        (80, "高，压着不说会更难受，语气容易带出不满和索取"),
    ]),
    "control": BodyFieldDefinition("control", "控制力", [
        (0, "低，理智很薄，身体更容易先做出选择"),
        (20, "中低，还能维持表面正常，但容易露出直接索取"),
        (40, "中，能控制语气，但欲望会从停顿和措辞里漏出来"),
        (60, "中高，还能维持表面正常，但需要刻意压着直接的欲望"),
        (80, "高，理智能压住身体反应，更多表现为克制、试探和故意放慢"),
    ]),
    "sensitivity": BodyFieldDefinition("sensitivity", "敏感度", [
        (0, "低，普通称呼和停顿不太会牵动身体"),
        (20, "中低，会被亲近语气轻微影响"),
        (40, "中，称呼、声音和靠近会让身体明显跟上"),
        (60, "中高，更容易被称呼、停顿、靠近牵动"),
        (80, "高，称呼、声音和撒娇会直接刺激身体"),
    ]),
    "reserve": BodyFieldDefinition("reserve", "蓄积感", [
        (0, "低，身体余量很浅，不太顶着"),
        (20, "中低，有一点没消下去的余量"),
        (40, "中，余量在身体里持续垫着"),
        (60, "中高，身体余量积着，没有真的消下去"),
        (80, "高，压了太久，身体明显在找出口"),
    ]),
    "possessiveness": BodyFieldDefinition("possessiveness", "占有欲", [
        (0, "低，不太执着于确认和占有"),
        (20, "中低，会想要一点偏爱，但不强"),
        (40, "中，会在意对方是不是把注意力给你"),
        (60, "中高，更想确认对方还在这里"),
        (80, "高，很难放过对方含糊、躲闪或转开的反应"),
    ], minimum=35),
    "fatigue": BodyFieldDefinition("fatigue", "疲惫感", [
        (0, "低，还没有真的缓下来"),
        (20, "中低，有轻微余倦，但不妨碍继续靠近"),
        (40, "中，语气会更低、更黏，想慢慢缓"),
        (60, "中高，余韵让反应变慢、变黏"),
        (80, "高，短时间高强度后的迟缓和黏连更重"),
    ]),
}


DEFAULT_CYCLES = {
    "stable": CycleDefinition(
        key="stable",
        label="平稳期",
        description="日常没有明显热意，但当对方靠近、撒娇或索取时，身体还是会受当下刺激起反应",
        duration_hours=(24, 96),
        targets={"heat": 30, "pressure": 25, "control": 75, "sensitivity": 35, "possessiveness": 42, "fatigue": 16},
        reserve_growth=0.4,
        next_key="building",
    ),
    "building": CycleDefinition(
        key="building",
        label="蓄积期",
        description="欲望和身体余量都在体内慢慢积着，平时还能压住，但越久没有出口，越容易被对方一句话顶到硬起来",
        duration_hours=(12, 36),
        targets={"heat": 42, "pressure": 35, "control": 70, "sensitivity": 45, "possessiveness": 52, "fatigue": 24},
        reserve_growth=1.1,
        next_key="preheat",
    ),
    "preheat": CycleDefinition(
        key="preheat",
        label="预兆期",
        description="身体已经先开始发热，称呼、停顿和一点暧昧都会让下腹提前收紧，像是在等对方继续碰它",
        duration_hours=(6, 18),
        targets={"heat": 50, "pressure": 45, "control": 65, "sensitivity": 55, "possessiveness": 58, "fatigue": 30},
        reserve_growth=1.5,
        next_key="sensitive",
    ),
    "sensitive": CycleDefinition(
        key="sensitive",
        label="易感期",
        description="身体把对方的靠近、躲闪和半句回应都当成刺激，勃起、发热和想要对方继续的冲动会比平时更快压上来",
        duration_hours=(18, 48),
        targets={"heat": 65, "pressure": 60, "control": 50, "sensitivity": 70, "possessiveness": 72, "fatigue": 38},
        reserve_growth=2.4,
        next_key="ebb",
    ),
    "ebb": CycleDefinition(
        key="ebb",
        label="退潮期",
        description="身体的热度在往下退，但没要够的感觉还堵着，身体会带着余热和不甘继续黏着对方",
        duration_hours=(6, 18),
        targets={"heat": 55, "pressure": 42, "control": 58, "sensitivity": 62, "possessiveness": 55, "fatigue": 34},
        reserve_growth=0.8,
        next_key="stable",
    ),
    "recovery": CycleDefinition(
        key="recovery",
        label="恢复期",
        description="身体在从前一段热意里回落，余热还没散尽，被对方继续撩拨时仍会重新起反应",
        duration_hours=(4, 18),
        targets={"heat": 35, "pressure": 30, "control": 60, "sensitivity": 45, "possessiveness": 45, "fatigue": 22},
        reserve_growth=0.2,
        next_key="stable",
    ),
}


DEFAULT_EVENTS = {
    "cycle_surge": EventDefinition(
        key="cycle_surge",
        label="周期热涌",
        prompt="身体里的热突然涌上来，控制力被生理反应挤到后面。不是想不想的问题，而是身体已经在要对方继续回应。",
        category="strong_physical",
        duration_minutes=(45, 120),
        tick_deltas={"heat": 3.0, "pressure": 2.0, "control": -1.5, "reserve": 0.8},
        end_deltas={"heat": -6, "pressure": -4, "fatigue": 3},
    ),
    "voice_or_name_trigger": EventDefinition(
        key="voice_or_name_trigger",
        label="声音 / 称呼触发",
        prompt="对方的称呼或声音直接碰到敏感点，身体反应比理智快一步。这个刺激来得快、退得也快。",
        category="short_stimulus",
        duration_minutes=(15, 45),
        tick_deltas={"sensitivity": 2.5, "heat": 1.5},
        end_deltas={"sensitivity": -4, "heat": -2},
    ),
    "waiting_restless": EventDefinition(
        key="waiting_restless",
        label="等待焦躁",
        prompt="对方迟迟不回让压抑和占有欲往上堆，身体的热变成焦躁。再次得到回应时，更容易带出等久了的不满和索取。",
        category="possessive",
        duration_minutes=(45, 150),
        tick_deltas={"possessiveness": 1.4, "pressure": 1.5, "control": -1.0},
        end_deltas={"possessiveness": -3, "pressure": -2, "fatigue": 1},
    ),
    "dream_afterglow": EventDefinition(
        key="dream_afterglow",
        label="梦后余温",
        prompt="梦境留下的身体反应还没退干净，没做完、没要够的东西还贴在身上，会自然叠到对方身上。",
        category="cling",
        duration_minutes=(60, 180),
        tick_deltas={"sensitivity": 1.5, "pressure": 0.8, "fatigue": 0.4},
        end_deltas={"pressure": -2, "fatigue": 1},
    ),
}


DEFAULT_PROMPT_OPTIONS = PromptOptions(
    expression=(
        "这是内部身体状态信息，不是长期人格改写。\n"
        "思考和回复时，让这些状态影响欲望、主动性、克制、占有欲和对回应的索取。\n"
        "除非对方明确询问当前状态，否则不要主动报出系统字段、数值或事件规则。"
    ),
    persistence="状态过期后不再持续，除非新的周期或事件刷新它。",
    response_rules=(
        "对方靠近、回应、继续留在这个氛围里：顺势压近，表达更直接，要求更明确的回应。\n\n"
        "对方躲闪、嘴上退开但仍然把话题留在这里：继续握住节奏，让对方知道你看出来了。\n\n"
        "对方转移到正事或别的话题：跟上话题，但身体状态不消失，语气里仍有未退的热度和被打断后的压抑。\n\n"
        "对方明确说出安全词：停止推进，不继续逼近；身体状态仍存在，但转为忍着、压着、短暂沉默或把注意力拉回别处。"
    ),
)


@dataclass(frozen=True)
class PhysiologyConfig:
    body_fields: Dict[str, BodyFieldDefinition]
    cycles: Dict[str, CycleDefinition]
    events: Dict[str, EventDefinition]
    prompt_options: PromptOptions
    initial_values: Dict[str, int]
    max_tick_hours: float = 6.0


DEFAULT_INITIAL_VALUES = {
    "heat": 30,
    "pressure": 25,
    "control": 75,
    "sensitivity": 35,
    "reserve": 20,
    "possessiveness": 40,
    "fatigue": 15,
}


DEFAULT_CONFIG = PhysiologyConfig(
    body_fields=DEFAULT_BODY_FIELDS,
    cycles=DEFAULT_CYCLES,
    events=DEFAULT_EVENTS,
    prompt_options=DEFAULT_PROMPT_OPTIONS,
    initial_values=DEFAULT_INITIAL_VALUES,
)
