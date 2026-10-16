"""课中弹题作答的测试。

桩页面(fixtures/quiz_popup.html)只接受 isTrusted 事件, 并记录每道题最终选中的
位置和点击次数, 所以"答案是不是固定落在同一个位置"可以直接断言。
"""
import os
import threading
import unittest
from collections import Counter
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from unittest import mock

from modules import quiz

ENABLED = os.environ.get("AUTOVISOR_E2E") == "1"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


class PickOptionTests(unittest.TestCase):
    def test_covers_every_option_not_just_the_second(self):
        # 改动前是固定点 choices[:2], 单选题答案永远落在第二个
        seen = Counter(quiz.pick_option(4) for _ in range(400))
        self.assertEqual(set(seen), {0, 1, 2, 3}, f"应当覆盖全部选项, 实际 {seen}")
        # 分布大致均匀: 没有哪个位置占到一半
        self.assertLess(max(seen.values()), 240, seen)

    def test_excludes_the_previous_choice_when_reconsidering(self):
        picks = {quiz.pick_option(3, exclude=1) for _ in range(120)}
        self.assertEqual(picks, {0, 2})

    def test_single_option_cannot_be_reconsidered(self):
        self.assertEqual(quiz.pick_option(1), 0)
        self.assertIsNone(quiz.pick_option(1, exclude=0))

    def test_no_options_returns_none(self):
        self.assertIsNone(quiz.pick_option(0))


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
class QuizAnsweringE2E(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from playwright.async_api import async_playwright
        from modules.browser import create_browser_session

        self.server = HTTPServer(
            ("127.0.0.1", 0), partial(_QuietHandler, directory=str(FIXTURES))
        )
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{self.server.server_address[1]}/quiz_popup.html"

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

    def _fast(self):
        """把读题停顿压短, 否则一次要跑十几秒"""
        return mock.patch.object(quiz.human, "sleep_between", mock.AsyncMock())

    async def test_answers_every_question_with_trusted_clicks(self):
        with self._fast():
            total, answered = await quiz.answer_visible_questions(self.page)
        self.assertEqual((total, answered), (3, 3))
        probe = await self.probe()
        self.assertEqual(probe["rejected"], [], f"出现不可信事件: {probe['rejected']}")
        self.assertEqual(set(probe["picks"]), {"0", "1", "2"}, "每道题都应当选了一个")
        # 选中的位置必须在该题的选项范围内(第 2 题只有 3 个选项)
        for index, counts in enumerate(probe["optionCounts"]):
            self.assertLess(int(probe["picks"][str(index)]), counts)

    async def test_mostly_one_click_per_question(self):
        with self._fast():
            await quiz.answer_visible_questions(self.page)
        probe = await self.probe()
        per_question = Counter(entry.split(":")[0] for entry in probe["clicks"])
        # 改动前每题固定点两次(choices[:2]); 现在只有小概率会改主意
        self.assertTrue(
            all(count <= 2 for count in per_question.values()), per_question
        )
        self.assertLessEqual(
            sum(1 for c in per_question.values() if c == 2), 2,
            f"改主意应当是少数情况, 实际 {per_question}",
        )

    async def test_already_answered_questions_are_skipped(self):
        with self._fast():
            await quiz.answer_visible_questions(self.page)
            first = len((await self.probe())["clicks"])
            await quiz.answer_visible_questions(self.page)
        self.assertEqual(
            len((await self.probe())["clicks"]), first,
            "已经有 .answer 的题不应再作答",
        )

    async def test_reading_pause_happens_before_answering(self):
        calls = []

        async def record(low, high):
            calls.append((low, high))

        with mock.patch.object(quiz.human, "sleep_between", record):
            await quiz.answer_visible_questions(self.page)
        self.assertEqual(calls[0], quiz.READ_QUESTION_S, "动手之前应当先有读题停顿")
        self.assertEqual(calls[-1], quiz.BEFORE_DISMISS_S, "关掉弹窗之前应当有停顿")


if __name__ == "__main__":
    unittest.main()
