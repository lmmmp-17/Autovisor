"""课中弹题作答。

改动前的行为(modules/tasks.py 里的 skip_questions):

    for each in choices[:2]:          # 固定点"前两个"选项
        await each.click(timeout=500)
        await page.wait_for_timeout(100)

问题不在于乱选——这类弹题本来就是随便选一个关掉——而在于它选得太有规律:

* 单选题点第一个再点第二个, 最终答案永远落在第二个选项上, 并且产生两次选择事件;
* 选项之间固定 100ms, 弹题出现到关闭总共一秒多, 没有任何读题时间;
* 用 Playwright 的 locator.click(), 一步瞬移到选项几何中心, 按下抬起没有间隔。

现在改成: 随机选一个, 带读题停顿, 走有轨迹的真实点击, 并且小概率"改一次主意"
(先点一个再换另一个)——人确实会这么做, 但不是每道题都做。

依旧不尝试答对: 判断对错要另外一套东西, 不在这里的职责范围内。
"""
from playwright.async_api import Page
from playwright._impl._errors import TargetClosedError

from modules import human
from modules.logger import Logger
from modules.pointer import human_click

logger = Logger()

QUESTION_PANEL = ".el-scrollbar__view"
QUESTION_NUMBER = ".number"
EXISTING_ANSWER = ".answer"
OPTION = ".topic-item"

# 单次点击的等待上限: 弹题上的元素要么在, 要么这道题不长这样
OPTION_CLICK_TIMEOUT_MS = 4000

# 看到弹题之后的读题时间
READ_QUESTION_S = (2.5, 7.0)
# 选项之间、题目之间
BETWEEN_OPTIONS_S = (0.6, 1.8)
BETWEEN_QUESTIONS_S = (1.2, 3.5)
# 答完到关掉弹窗
BEFORE_DISMISS_S = (0.8, 2.4)
# 改主意的概率: 先点一个, 再换成另一个
RECONSIDER_CHANCE = 0.18


def pick_option(count: int, exclude: int | None = None) -> int | None:
    """从 count 个选项里随机挑一个, 可以排除某一个(用于改主意)。"""
    if count <= 0:
        return None
    candidates = [i for i in range(count) if i != exclude]
    if not candidates:
        return None
    return human.pick(candidates)


async def _click_option(page: Page, index: int) -> bool:
    options = page.locator(OPTION)
    if index >= await options.count():
        return False
    await human_click(options.nth(index), timeout=OPTION_CLICK_TIMEOUT_MS)
    return True


async def answer_one_question(page: Page) -> bool:
    """给当前显示的这道题选一个答案。选了返回 True。"""
    options = page.locator(OPTION)
    count = await options.count()
    choice = pick_option(count)
    if choice is None:
        logger.debug_throttled("quiz:no_option", "这道题没有可选项, 跳过")
        return False

    if not await _click_option(page, choice):
        return False

    # 偶尔改一次主意: 人会先点一个再换, 但不是每题都换
    if count > 1 and human.chance(RECONSIDER_CHANCE):
        second = pick_option(count, exclude=choice)
        if second is not None:
            await human.sleep_between(*BETWEEN_OPTIONS_S)
            await _click_option(page, second)
    return True


async def answer_visible_questions(page: Page) -> tuple[int, int]:
    """逐题作答, 返回 (题目数, 已作答数)。已经有答案的题跳过。"""
    panel = page.locator(QUESTION_PANEL).first
    numbers = panel.locator(QUESTION_NUMBER)
    total = await numbers.count()
    if total == 0:
        return 0, 0

    # 弹题刚出来先读一会儿题, 再动手
    await human.sleep_between(*READ_QUESTION_S)

    answered = 0
    for index in range(total):
        if index > 0:
            await human.sleep_between(*BETWEEN_QUESTIONS_S)
        try:
            await human_click(numbers.nth(index), timeout=OPTION_CLICK_TIMEOUT_MS)
        except TargetClosedError:
            raise
        except Exception as exc:
            logger.debug_throttled(
                "quiz:number", f"切到第 {index + 1} 题失败: {logger.summarize_exception(exc)}"
            )
            continue
        if await page.locator(EXISTING_ANSWER).count():
            continue
        if await answer_one_question(page):
            answered += 1

    await human.sleep_between(*BEFORE_DISMISS_S)
    return total, answered
