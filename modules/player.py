"""点播放器自己的控件, 而不是在页面里写 video 属性。

结构来自线上页面(``--check-player`` 实测):

    .videoArea                        指针移上去控制栏才展开, 平时是收起的
    .volumeBox > .volumeIcon          静音开关
    .speedBox  > span                 当前倍速标签, 文字形如 "X 1.0"
    .speedBox  > .speedList
        .speedTab 'X 1.5' / 'X 1.25' / 'X 1.0'

两个坑:

1. 控制栏默认收起, 不先把指针移到视频区域, 下面的控件拿不到尺寸也点不动。
2. ``.speedTab`` 的类名后缀和倍速值对不上(``speedTab10`` 是 1.25 倍), 所以按
   标签文字里的数字匹配, 不按类名。

每个函数都返回"是否走通了真实控件"。走不通时由调用方退回原来的属性写入——
那样会留下痕迹, 但不会把功能弄坏。
"""
import re

from playwright.async_api import Page
from playwright._impl._errors import TargetClosedError

from modules import human
from modules.logger import Logger
from modules.pointer import human_click, pointer_for

logger = Logger()

VIDEO_AREA = ".videoArea"
VOLUME_BOX = ".volumeBox"
VOLUME_ICON = ".volumeBox .volumeIcon"
SPEED_BOX = ".speedBox"
SPEED_LABEL = ".speedBox span"
SPEED_TAB = ".speedBox .speedList .speedTab"

# 控件交互的等待上限: 控制栏要么马上展开, 要么就是这个播放器不长这样
CONTROL_TIMEOUT_MS = 4000

_RATE_IN_LABEL = re.compile(r"(\d+(?:\.\d+)?)")


def parse_rate_label(text: str) -> float | None:
    """从 "X 1.25" 这类标签里取出倍速值。"""
    match = _RATE_IN_LABEL.search(text or "")
    return float(match.group(1)) if match else None


async def _center_of(page: Page, selector: str):
    box = await page.locator(selector).first.bounding_box()
    if not box or box["width"] <= 0 or box["height"] <= 0:
        return None
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


async def _move_onto(page: Page, selector: str) -> bool:
    """把指针移到元素中心, 再补一次极小的移动。

    补这一下是必须的, 不是为了像人。收起的控制栏靠祖先的 pointer-events: none
    挡住, 指针落点命中的是底下的视频; 视频进入 hover 后控制栏才变可交互, 而浏览器
    要再收到一个鼠标事件才会重新做命中测试。移动轨迹是带弧度的, 中途可能甩出视频
    区域让控制栏重新收起, 所以不能指望落点那一下就位——少了这一步, 倍速菜单会
    间歇性打不开。
    """
    center = await _center_of(page, selector)
    if center is None:
        return False
    pointer = pointer_for(page)
    await pointer.move_to(*center)
    await page.mouse.move(round(pointer.x) + 1, round(pointer.y))
    pointer.x += 1
    await human.sleep(0.4)
    return True


async def reveal_controls(page: Page) -> bool:
    """把指针移到视频区域, 让控制栏展开。

    用原始鼠标移动而不是 locator.hover(): 后者带可交互性检查, 而这里要的只是
    "指针在那儿", 元素不需要先满足可点击条件。
    """
    return await _move_onto(page, VIDEO_AREA)


async def _open_speed_menu(page: Page) -> bool:
    if not await _move_onto(page, SPEED_BOX):
        return False
    return await page.locator(SPEED_TAB).first.is_visible()


async def current_rate_label(page: Page) -> float | None:
    label = page.locator(SPEED_LABEL).first
    if not await label.count():
        return None
    return parse_rate_label(await label.inner_text())


async def set_rate_by_menu(page: Page, rate: float) -> bool:
    """用播放器的倍速菜单设成 rate。走通返回 True。

    这样倍速标签由播放器自己更新, 不需要我们去改写它的文字。
    """
    try:
        if not await reveal_controls(page):
            logger.debug_throttled("player:reveal", "倍速菜单跳过: 控制栏没有展开")
            return False
        if not await _open_speed_menu(page):
            logger.debug_throttled("player:speed_menu", "倍速菜单跳过: 选项没有出现")
            return False

        tabs = page.locator(SPEED_TAB)
        for index in range(await tabs.count()):
            tab = tabs.nth(index)
            if parse_rate_label(await tab.inner_text()) != rate:
                continue
            await human_click(tab, timeout=CONTROL_TIMEOUT_MS)
            await human.sleep(0.6)
            return await current_rate_label(page) == rate
        logger.debug_throttled(
            "player:speed_absent", f"倍速菜单里没有 {rate} 这一档"
        )
        return False
    except TargetClosedError:
        raise
    except Exception as exc:
        logger.debug_throttled(
            "player:speed", f"倍速菜单操作失败: {logger.summarize_exception(exc)}"
        )
        return False


async def mute_by_button(page: Page) -> bool:
    """点播放器的音量按钮静音。走通返回 True。

    静音图标由播放器自己切换, 不需要我们去加 volumeNone 这个类。
    """
    try:
        if not await reveal_controls(page):
            return False
        if not await _move_onto(page, VOLUME_BOX):
            return False
        icon = page.locator(VOLUME_ICON).first
        if not await icon.count():
            logger.debug_throttled("player:volume_absent", "静音跳过: 没有音量按钮")
            return False
        await human_click(icon, timeout=CONTROL_TIMEOUT_MS)
        await human.sleep(0.5)
        state = await page.evaluate(
            """() => {
                const v = document.querySelector('video');
                return v ? { muted: v.muted, volume: v.volume } : null;
            }"""
        )
        return bool(state) and (state["muted"] or state["volume"] == 0)
    except TargetClosedError:
        raise
    except Exception as exc:
        logger.debug_throttled(
            "player:volume", f"音量按钮操作失败: {logger.summarize_exception(exc)}"
        )
        return False


async def play_by_click(page: Page) -> bool:
    """点视频区域起播。走通(视频确实在放了)返回 True。

    只在确认处于暂停时调用: 这个区域是开关, 正在播放时点一下会变成暂停。
    """
    try:
        area = page.locator(VIDEO_AREA).first
        if not await area.count():
            return False
        await human_click(area, timeout=CONTROL_TIMEOUT_MS)
        await human.sleep(0.7)
        paused = await page.evaluate(
            "() => { const v = document.querySelector('video'); return v ? v.paused : null; }"
        )
        return paused is False
    except TargetClosedError:
        raise
    except Exception as exc:
        logger.debug_throttled(
            "player:play", f"点击起播失败: {logger.summarize_exception(exc)}"
        )
        return False
