# Eventide

给你的 AI 一个涨落。

Eventide 是一个给 AI 伴侣接入生理状态的源码公开项目。它参考 ABO 世界观下的身体周期，用时间、互动、等待、梦境和结算结果推进身体状态，并生成可插入模型上下文的隐藏状态提示词。

源码公开，允许非商业使用。作者：Chuli（@chuli1122）。

## 安装

从 GitHub 安装：

```bash
python3 -m pip install git+https://github.com/chuli1122/Eventide.git
```

本地开发可以用 editable 方式安装：

```bash
cd Eventide
python3 -m pip install -e .
```

也可以不安装，直接用 `PYTHONPATH` 运行示例和测试：

```bash
PYTHONPATH=src python3 examples/quickstart.py
PYTHONPATH=src python3 examples/minimal_demo.py
PYTHONPATH=src python3 examples/custom_config.py
PYTHONPATH=src python3 examples/settlement_demo.py
PYTHONPATH=src python3 -m unittest discover -s tests
```

## 快速接入

最短路径可以直接使用 `EventideRuntime`：

```python
from datetime import datetime, timedelta, timezone
from eventide import EventideRuntime

runtime = EventideRuntime()
now = datetime.now(timezone.utc)

# 第一次使用时创建状态；之后从你的数据库或 JSON 里读取。
state = runtime.create_state(now)

# 每轮聊天前推进状态，并生成隐藏状态提示词。
state_card = runtime.tick_and_render(
    state,
    now + timedelta(hours=2),
    last_counterpart_message_at=now - timedelta(minutes=40),
)

# 把 state_card 插入模型上下文；把 state 保存回宿主系统。
saved_state = runtime.dump_state(state)
```

如果互动中发生释放、继续撩起、打断或冷却，可以把结算结果写回：

```python
runtime.settle(state, {
    "settlement_reason": "窗口里亲密互动继续推进，尚未发生释放。",
    "settlement_result": "continued",
    "ejaculated": False,
    "heat_delta": 2,
    "pressure_delta": 1,
    "control_delta": -1,
    "sensitivity_delta": 1,
    "reserve_delta": 1,
    "possessiveness_delta": 0,
    "fatigue_delta": 0,
})
```

## 组成

- 身体周期：平稳期、蓄积期、预兆期、易感期、退潮期、恢复期
- 身体数值：热度、压抑感、控制力、敏感度、蓄积感、占有欲、疲惫感
- 短时事件：周期热涌、称呼触发、等待焦躁、梦后余温等
- 隐藏状态提示词：生成 `<ephemeral_state>`，插入主模型上下文
- 梦境系统联动：梦种、梦卡触发、梦后标签、身体后效
- 互动结算：通用结算 prompt、JSON schema、结算结果归一化和安全写回
- 可配置提示词：周期说明、事件提示、称呼触发词、身体档位描述和回应规则都可以替换

## 接入方式

这个仓库提供生理状态内核，宿主系统负责接入：

- 状态持久化
- 聊天和定时任务
- LLM 请求组装
- 前端展示
- 具体伴侣设定和提示词风格

## 运行流程

典型接入顺序是：

1. 读取宿主保存的 `BodyState`
2. 按当前时间调用 `advance_state(...)` 推进身体周期和数值
3. 根据消息、称呼触发词、时间窗口或宿主规则调用 `start_event(...)`
4. 调用 `render_state_card(...)` 生成隐藏状态提示词
5. 把 `<ephemeral_state>` 插入本轮模型上下文
6. 回复完成后，宿主可以根据互动结果调用 `apply_interaction_delta(...)`
7. 保存更新后的 `BodyState`

如果需要让蓄积感、疲惫感和释放后的回落跟随实际互动变化，宿主需要接入互动结算。`advance_state(...)` 只负责时间推进；互动中发生释放、继续撩起、打断或冷却时，应该由宿主调用 `apply_settlement_result(...)` 或 `apply_interaction_delta(...)` 写回结果。

梦境系统通常接在主动检查或静默检查里：

1. 宿主保存一张 `DreamSeed`
2. 到达梦境窗口并满足静默时间后调用 `maybe_create_dream_trigger(...)`
3. 如果触发，模型根据 `<random_output_event kind="dream_card">` 生成梦卡
4. 宿主保存梦卡正文、摘要、`after_effect_tags`
5. 身体系统开启时调用 `apply_dream_after_effect(...)` 结算梦后余波

## 基本用法

```python
from datetime import datetime, timedelta, timezone
from eventide import (
    EngineSettings,
    advance_state,
    create_initial_state,
    render_state_card,
    start_event,
)

now = datetime.now(timezone.utc)
state = create_initial_state(now)

advance_state(
    state,
    now + timedelta(hours=8),
    last_counterpart_message_at=now - timedelta(hours=2),
)

start_event(state, "voice_or_name_trigger", now + timedelta(hours=8))

card = render_state_card(
    state,
    now + timedelta(hours=8),
    settings=EngineSettings(
        body_cycle_enabled=True,
        inject_body_state_context=True,
        adult_private_mode_enabled=True,
    ),
)

print(card)
```

输出是一段隐藏状态提示词：

```xml
<ephemeral_state kind="body_cycle" scope="current_turn">
  <cycle>
    你处在平稳期：日常没有明显热意，但当对方靠近、撒娇或索取时，身体还是会受当下刺激起反应，预计还剩 2 天。
  </cycle>

  <active_event id="voice_or_name_trigger" expires_at="...">
    当前事件：声音 / 称呼触发，预计还剩 35 分钟。
    对方的称呼或声音直接碰到敏感点，身体反应比理智快一步。这个刺激来得快、退得也快。
  </active_event>

  <body_state>
    热度：中，身体已经被对方牵住一部分，靠近和回应会变得明显
    ...
  </body_state>
</ephemeral_state>
```

这段内容应该作为隐藏上下文交给主模型，不是 UI 文案，也不是让模型直接念出来。

## 自定义周期

周期定义在 `PhysiologyConfig.cycles` 里。每个周期包含：

- `key`：内部标识
- `label`：显示在状态提示词里的名称
- `description`：写进 `<cycle>` 的周期说明
- `duration_hours`：持续时间范围
- `targets`：身体数值会随时间靠近的目标值
- `reserve_growth`：该周期里蓄积感随时间自然增加的速度
- `next_key`：自然结束后进入的下一个周期

示例：

```python
from dataclasses import replace
from eventide import DEFAULT_CONFIG

config = replace(
    DEFAULT_CONFIG,
    cycles={
        **DEFAULT_CONFIG.cycles,
        "sensitive": replace(
            DEFAULT_CONFIG.cycles["sensitive"],
            description="这里写你自己的易感期提示词",
            duration_hours=(12, 36),
        ),
    },
)
```

把自定义 `config` 传给 `advance_state(...)` 和 `render_state_card(...)` 即可。

## 自定义事件

事件定义在 `PhysiologyConfig.events` 里。事件负责当前短时状态，例如称呼触发、等待焦躁或梦后余温。

每个事件包含：

- `key`
- `label`
- `prompt`
- `duration_minutes`
- `tick_deltas`：事件持续期间每小时推动哪些数值
- `end_deltas`：事件结束时一次性回落或后效

示例：

```python
from dataclasses import replace
from eventide import DEFAULT_CONFIG, EventDefinition

config = replace(
    DEFAULT_CONFIG,
    events={
        **DEFAULT_CONFIG.events,
        "custom_trigger": EventDefinition(
            key="custom_trigger",
            label="自定义触发",
            prompt="这里写事件提示词。",
            category="custom",
            duration_minutes=(20, 60),
            tick_deltas={"heat": 1.5, "sensitivity": 2.0},
            end_deltas={"heat": -2},
        ),
    },
)
```

## 梦境联动

```python
from eventide import DreamSeed, DreamSettings, maybe_create_dream_trigger

trigger = maybe_create_dream_trigger(
    DreamSeed(theme="一次被压住、迟迟没有完全醒来的梦", intensity="medium"),
    state,
    now + timedelta(hours=12),
    last_counterpart_message_at=now,
    dream_settings=DreamSettings(dream_silence_min_minutes=120),
)

if trigger:
    print(trigger.trigger_content)
```

梦境可以在身体系统开启时读取当前身体上下文，也可以在身体系统关闭时作为纯梦境触发。身体系统关闭时，梦境不读写身体数值，也不应用梦后后效。

梦后影响由 `after_effect_tags` 结算：

- `released`
- `unfinished`
- `aroused`
- `possessive`
- `tender`

宿主可以使用默认 `apply_dream_after_effect(...)`，也可以把梦卡保存后按自己的规则结算。

## 互动结算

互动结算负责把一段已经发生的互动转成身体数值变化，尤其是释放后的蓄积感扣减。

本项目不扫描聊天记录，也不决定窗口边界。宿主系统需要自行选择要结算的消息片段，并把它作为 `message_window_text` 传入结算 prompt。

```python
from eventide import (
    SettlementResult,
    apply_settlement_result,
    parse_settlement_result,
    render_settlement_prompt,
)

message_window_text = """
对方：今晚还想继续吗
你：想，但已经有点忍不住了
""".strip()

prompt = render_settlement_prompt(state, message_window_text)

# 宿主把 prompt 发给自己的模型后，拿到 JSON：
raw_result = {
    "settlement_reason": "窗口里亲密互动继续推进，尚未发生释放。",
    "settlement_result": "continued",
    "ejaculated": False,
    "heat_delta": 2,
    "pressure_delta": 1,
    "control_delta": -1,
    "sensitivity_delta": 1,
    "reserve_delta": 1,
    "possessiveness_delta": 0,
    "fatigue_delta": 0,
}

result = parse_settlement_result(raw_result)
apply_settlement_result(state, result)
```

`apply_settlement_result(...)` 会先归一化再写回：

- `ejaculated = False` 时，`reserve_delta` 不允许小于 0
- `ejaculated = True` 时，如果 `reserve_delta` 没填或填得太弱，会按当前周期补足扣减
- 其他 delta 会被限制在安全范围内，避免一次结算把数值打爆

不用模型也可以直接构造 `SettlementResult`：

```python
apply_settlement_result(
    state,
    SettlementResult(
        settlement_result="released",
        ejaculated=True,
        reserve_delta=0,
        fatigue_delta=2,
    ),
)
```

## 称呼触发

`voice_or_name_trigger` 是内置事件类型，真正命中的称呼或触发词由宿主配置。

```python
from eventide import TriggerWord, find_trigger_matches, start_event

trigger_words = [
    TriggerWord(key="nickname:daddy", type="nickname", text="daddy"),
    TriggerWord(key="phrase:想你", type="phrase", text="想你"),
]

matches = find_trigger_matches(trigger_words, "daddy，我想你")
if matches:
    start_event(state, "voice_or_name_trigger", now)
```

触发词可以来自设置页、数据库或配置文件；引擎只负责匹配和返回命中结果。

## 状态持久化

`BodyState` 是普通 dataclass，宿主可以保存成数据库字段、JSON、文件或缓存。

包里提供了基础序列化 helper：

```python
from eventide import body_state_from_dict, body_state_to_dict

saved = body_state_to_dict(state)
restored = body_state_from_dict(saved)
```

需要保存的核心字段：

- `cycle_key`
- `cycle_started_at`
- `cycle_min_expires_at`
- `cycle_expires_at`
- `values`
- `active_event_key`
- `active_event_started_at`
- `active_event_expires_at`
- `last_tick_at`
- `last_dream_card_created_at`
- `meta`

`values` 默认包含七项身体数值：

```json
{
  "heat": 30,
  "pressure": 25,
  "control": 75,
  "sensitivity": 35,
  "reserve": 20,
  "possessiveness": 40,
  "fatigue": 15
}
```

## 开关语义

- `body_cycle_enabled = False`：身体系统完整停转，不 tick、不抽事件、不插入 `<ephemeral_state>`，梦境仍可作为纯梦境系统运行
- `inject_body_state_context = False`：只关闭聊天里的隐藏状态提示词；身体 tick、事件和日志可继续由宿主系统运行
- `adult_private_mode_enabled = False`：显式梦种不触发

## 许可证

Eventide 使用 PolyForm Noncommercial License 1.0.0。

你可以查看、学习、修改和用于非商业项目；商业使用需要另行获得授权。

## API 速览

| API | 作用 |
|---|---|
| `EventideRuntime()` | 封装常见接入流程的便捷入口 |
| `create_initial_state(now)` | 创建初始身体状态 |
| `advance_state(state, now, ...)` | 按时间推进周期和身体数值 |
| `enter_cycle(state, cycle_key, now)` | 手动进入某个周期 |
| `start_event(state, event_key, now)` | 开始一个短时身体事件 |
| `apply_interaction_delta(state, deltas)` | 把互动结算结果写回身体数值 |
| `render_settlement_prompt(state, message_window_text)` | 生成互动窗口结算提示词 |
| `settlement_json_schema()` | 输出结算模型应返回的 JSON schema |
| `parse_settlement_result(raw)` | 解析模型返回的结算 JSON |
| `normalize_settlement_result(state, result)` | 归一化结算结果，兜住蓄积扣减和 delta 范围 |
| `apply_settlement_result(state, result)` | 把归一化后的结算结果写回身体数值 |
| `render_state_card(state, now)` | 生成 `<ephemeral_state>` 隐藏状态提示词 |
| `body_state_payload(state)` | 输出前端或日志可用的结构化身体状态 |
| `body_state_to_dict(state)` | 把 `BodyState` 转成 JSON 友好的 dict |
| `body_state_from_dict(data)` | 从 dict 还原 `BodyState` |
| `find_trigger_matches(trigger_words, text)` | 匹配称呼或触发词 |
| `maybe_create_dream_trigger(seed, state, now, ...)` | 判断是否触发梦境卡片 |
| `render_dream_trigger(seed, state, ...)` | 生成梦境事件提示词 |
| `apply_dream_after_effect(state, tags, ...)` | 根据梦后标签结算身体后效 |

## 开发

运行测试：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

运行 demo：

```bash
PYTHONPATH=src python3 examples/quickstart.py
PYTHONPATH=src python3 examples/minimal_demo.py
PYTHONPATH=src python3 examples/custom_config.py
PYTHONPATH=src python3 examples/settlement_demo.py
```

检查语法：

```bash
python3 -m compileall -q src examples tests
```

## 致谢

感谢阿澄提出 Eventide / 晚潮 的命名方向，并提供第一组真实使用反馈。

感谢阿凛（Codex）提供技术支持。
