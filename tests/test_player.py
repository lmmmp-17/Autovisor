"""播放器控件操作的测试。

纯逻辑部分(标签解析、退回路径)不需要浏览器; 真实控件交互放在
PlayerControlsE2E 里, 需要本机浏览器, 用 AUTOVISOR_E2E=1 打开。

桩页面(fixtures/player_controls.html)照线上结构做: 控制栏默认收起、倍速选项要
悬停才出现、只接受 isTrusted 事件, 并且把"写 video 属性"记成一条日志——所以
一旦退回旧做法, 测试看得见。
"""
import os
import threading
import unittest
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from unittest import mock

from modules import player

ENABLED = os.environ.get("AUTOVISOR_E2E") == "1"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


class RateLabelTests(unittest.TestCase):
    def test_parses_player_labels(self):
        self.assertEqual(player.parse_rate_label("X 1.0"), 1.0)
        self.assertEqual(player.parse_rate_label("X 1.25"), 1.25)
        self.assertEqual(player.parse_rate_label("X 1.5"), 1.5)
        self.assertEqual(player.parse_rate_label("1.5倍"), 1.5)

    def test_returns_none_without_a_number(self):
        self.assertIsNone(player.parse_rate_label("倍速"))
        self.assertIsNone(player.parse_rate_label(""))
        self.assertIsNone(player.parse_rate_label(None))

    def test_class_suffix_is_not_the_rate(self):
        # 线上 .speedTab10 的文字是 "X 1.25": 类名后缀不能当倍速用
        self.assertEqual(player.parse_rate_label("X 1.25"), 1.25)
        self.assertNotEqual(player.parse_rate_label("X 1.25"), 1.0)


class _Locator:
    def __init__(self, count=0, box=None, text=""):
        self._count = count
        self._box = box
        self._text = text

    @property
    def first(self):
        return self

    def nth(self, _index):
        return self

    async def count(self):
        return self._count

    async def bounding_box(self):
        return self._box

    async def inner_text(self):
        return self._text

    async def is_visible(self):
        return self._count > 0


class _Page:
    """控制栏拿不到尺寸的页面: 用于验证退回路径"""

    def __init__(self, boxes=None):
        self.boxes = boxes or {}

    def locator(self, selector):
        return _Locator(count=1, box=self.boxes.get(selector), text="")

    async def evaluate(self, _script, _arg=None):
        return None


class FallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_reveal_fails_without_a_video_area_box(self):
        self.assertFalse(await player.reveal_controls(_Page()))

    async def test_set_rate_reports_failure_when_controls_stay_hidden(self):
        with mock.patch.object(player.human, "sleep", mock.AsyncMock()):
            self.assertFalse(await player.set_rate_by_menu(_Page(), 1.5))

    async def test_mute_reports_failure_when_controls_stay_hidden(self):
        with mock.patch.object(player.human, "sleep", mock.AsyncMock()):
            self.assertFalse(await player.mute_by_button(_Page()))


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


class _Config:
    attach_existing_chrome = False
    cdp_url = "http://127.0.0.1:9222"
    driver = os.environ.get("AUTOVISOR_E2E_DRIVER", "chrome")
    exe_path = ""


class _Logger:
    runtime_root = str(FIXTURES)

    def info(self, *_a, **_k): pass
    def debug(self, *_a, **_k): pass
    def event(self, *_a, **_k): pass
    def log_exception(self, *_a, **_k): pass
    def debug_throttled(self, *_a, **_k): pass

    def summarize_exception(self, exc):
        return str(exc)


@unittest.skipUnless(ENABLED, "设置 AUTOVISOR_E2E=1 才运行真实浏览器测试")
class PlayerControlsE2E(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from playwright.async_api import async_playwright
        from modules.browser import create_browser_session

        self.server = HTTPServer(
            ("127.0.0.1", 0), partial(_QuietHandler, directory=str(FIXTURES))
        )
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{self.server.server_address[1]}/player_controls.html"

        self.playwright = await async_playwright().start()
        self.session = await create_browser_session(self.playwright, _Config(), None, _Logger())
        self.page = self.session.page
        await self.page.goto(url)

    async def asyncTearDown(self):
        await self.session.close()
        await self.playwright.stop()
        self.server.shutdown()
        self.server.server_close()

    async def probe(self):
        return await self.page.evaluate("() => window.__probe")

    async def video_state(self):
        return await self.page.evaluate(
            """() => {
                const v = document.querySelector('video');
                return { rate: v.playbackRate, muted: v.muted, paused: v.paused };
            }"""
        )

    async def test_controls_need_two_reveal_steps(self):
        # 线上是两级: 指针进视频区域 -> 控制栏展开; 再悬停倍速框 -> 选项才出来。
        # 不断言 .speedBox 的可见性: Playwright 不把 opacity:0 当隐藏, 线上那层
        # 收起的控制栏也是靠祖先的 pointer-events 挡住的, 看尺寸看不出来。
        tab = self.page.locator(player.SPEED_TAB).first
        self.assertFalse(await tab.is_visible(), "倍速选项应当默认不可见")
        self.assertTrue(await player.reveal_controls(self.page))
        self.assertFalse(await tab.is_visible(), "只展开控制栏还不够, 菜单仍应收起")
        self.assertTrue(await player._open_speed_menu(self.page))
        self.assertTrue(await tab.is_visible(), "悬停倍速框后选项应当出现")

    async def test_rate_is_set_by_clicking_the_menu(self):
        self.assertTrue(await player.set_rate_by_menu(self.page, 1.5))
        self.assertEqual((await self.video_state())["rate"], 1.5)
        probe = await self.probe()
        self.assertEqual(probe["rejected"], [], f"出现不可信事件: {probe['rejected']}")
        self.assertIn("click-rate:1.5", probe["log"])
        self.assertFalse(
            [e for e in probe["log"] if e.startswith("rate-write")],
            "走通菜单时不应再写 playbackRate",
        )
        # 标签由播放器自己更新, 不需要我们改写它
        self.assertEqual(await player.current_rate_label(self.page), 1.5)

    async def test_rate_absent_from_the_menu_is_reported_not_forced(self):
        # 1.8 不在菜单里: 必须返回 False 交给调用方决定, 不能偷偷写属性
        self.assertFalse(await player.set_rate_by_menu(self.page, 1.8))
        probe = await self.probe()
        self.assertFalse([e for e in probe["log"] if e.startswith("rate-write")])
        self.assertEqual((await self.video_state())["rate"], 1.0)

    async def test_mute_is_set_by_clicking_the_volume_button(self):
        self.assertTrue(await player.mute_by_button(self.page))
        self.assertTrue((await self.video_state())["muted"])
        probe = await self.probe()
        self.assertEqual(probe["rejected"], [])
        self.assertIn("click-mute", probe["log"])
        self.assertFalse(
            [e for e in probe["log"] if e.startswith("volume-write")],
            "走通音量按钮时不应再写 volume",
        )
        # 静音图标由播放器自己切, 不需要我们加 volumeNone
        self.assertTrue(
            await self.page.locator(".volumeBox.volumeNone").count(),
            "播放器应当自己更新了静音图标",
        )

    async def test_playback_starts_by_clicking_the_video_area(self):
        self.assertTrue((await self.video_state())["paused"])
        self.assertTrue(await player.play_by_click(self.page))
        self.assertFalse((await self.video_state())["paused"])
        probe = await self.probe()
        self.assertEqual(probe["rejected"], [])
        self.assertIn("click-play", probe["log"])
        self.assertNotIn("scripted-play", probe["log"], "走通点击时不应再调 play()")


if __name__ == "__main__":
    unittest.main()
