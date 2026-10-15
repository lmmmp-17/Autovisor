"""随机化原语。

脚本感很大一部分来自节拍: 每 2 秒整查一次播放器、每次点击后恰好等 1 秒。
这里的等待都以基准值为中心抖动, 并留一条长尾——真人的间隔不会整齐落在
同一个区间里。
"""
import asyncio
import random

_rng = random.SystemRandom()


def uniform(low: float, high: float) -> float:
    return _rng.uniform(low, high)


def chance(probability: float) -> bool:
    return _rng.random() < probability


def gauss_within(low: float, high: float) -> float:
    """在 [low, high] 内取一个靠中间的值(截断正态)。"""
    mid = (low + high) / 2
    value = _rng.gauss(mid, (high - low) / 6)
    return min(high, max(low, value))


def jitter(base: float, spread: float = 0.35) -> float:
    value = base * _rng.uniform(1 - spread, 1 + spread)
    if chance(0.08):
        value *= _rng.uniform(1.3, 2.1)
    return value


async def sleep(base: float, spread: float = 0.35) -> None:
    """以 base 秒为中心抖动的等待。"""
    await asyncio.sleep(jitter(base, spread))


async def sleep_between(low: float, high: float) -> None:
    await asyncio.sleep(_rng.uniform(low, high))
