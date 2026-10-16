

**本次更新:**

- 新增融合共享支持: 自动跳过弹窗、展开折叠目录、关闭弹窗后恢复播放, 并读取课时真实进度 ([#158](https://github.com/CXRunfree/Autovisor/pull/158)).

**近期更新:**

- 修复课程页卡死: 已读的"学前必读"弹窗是隐藏节点, 等它可见会一直等下去, 现在超时即跳过 ([#155](https://github.com/CXRunfree/Autovisor/pull/155)).
- 课时切换、目录识别的等待也加上超时, 异常页面不再长时间卡住.
- 支持 Python 3.13.

------
#### 一、程序介绍

**项目简介:**

这是一个可无人监督的自动化程序, 基于微软的 Playwright 框架, 由 Python 和 JavaScript 编写而成. 核心原理是使用浏览器模拟用户操作.

**程序功能:**

- **支持自动登录**
- **自动通过登录滑块验证(可选)**
- **自动播放和切换下一集**
- **自动跳过弹窗和弹题**
- **自动静音、设置指定倍速**
- **自动检测暂停并自动续播**
- **支持智慧共享课、翻转课、融合共享课**
- **支持刷习惯分**
- **支持隐藏窗口后台刷课**
- 启动时自动检查更新
- 后台实时更新学习进度
- macOS / Linux 支持源码运行
- 页面侧不留自动化痕迹: 不注入脚本, 点击、滚动、输入都是浏览器生成的真实输入 (见 **六、降低自动化特征**)
- 根据当前时间自动设置背景色(白天/夜晚)
- 完成章节时提示已完成时长
- 各种自定义配置

#### 二、发行版运行

1. 请确保系统为 Windows 10 及以上.

2. 发行版文件夹内自带 **config.ini** (可能没显示 `.ini` 后缀名), 使用 **文本编辑器** 打开.

3. 根据文件内的注释, 填写配置文件:

   - 默认启动系统自带的 Edge 浏览器;
   - 文件里的 **EXE_PATH 项** 用于自定义浏览器路径, 需要精确到**浏览器可执行文件的位置**, 可以保持默认不填;
   - 不知道浏览器的安装路径? 见下方 **五、常见问题**.
   - 确认 **保存修改** 后再退出.

   <p align="left"><img src="resources/markdown/config_detail.png" width="600" alt="config.ini 配置说明"></p>

4. 注意事项

   - **`config.ini` 配置项不需要加引号.**

   - **如果需要修改下载镜像源, 请编辑 `data/mirrors.json`**

5. 运行 **Autovisor.exe**, 会自动打开浏览器, 进入网课界面后就能自动刷课了!

   (如果未设置 **enableAutoCaptcha=True**, 则需要**手动完成**登录时的滑块验证)

**发行版目录说明:**

- `resources/`: 图片、脚本等程序资源.
- `packages/`: 自动下载的 NumPy、OpenCV 等运行时依赖.
- `data/`: 登录 Cookies 和镜像源配置.

#### 三、macOS / Linux 源码运行

- macOS: 需要 macOS 11 (Big Sur) 及以上 (Apple Silicon / Intel 均可) 和系统 Chrome 浏览器.
- Linux: 需要已安装 Google Chrome (`google-chrome`) 或 Microsoft Edge; 也可以把 `driver` 设为 `Chromium`, 由脚本自动下载.

先复制对应平台的模板并填写配置:

```bash
cp config.macos.ini.example config.macos.ini    # macOS
cp config.linux.ini.example config.linux.ini    # Linux
```

填入课程链接 (账号密码可留空, 用浏览器手动登录), 然后运行:

```bash
./run.sh
```

脚本会按系统自动选用 `config.macos.ini` 或 `config.linux.ini`, 也可以用 `--config` 指定. 首次运行会自动部署环境 (安装 `uv`、依赖和必要的浏览器), 之后直接启动. 环境或配置变化时会自动重新部署, 也可用 `./run.sh --setup` 强制重建. 旧的 `./run_macos.sh` 仍可使用.

说明:

- `enableHideWindow` 只在 Windows 上生效. macOS / Linux 上把浏览器窗口放到其它窗口后面、或挪到另一个工作区即可, 失焦不会打断播放; **不要最小化**, 最小化后页面会变成后台状态.
- Linux 上用 `Chromium` 时若报缺少系统库, 执行 `sudo uv run playwright install-deps chromium`.

#### 四、发行版下载

- Github: [Releases · CXRunfree/Autovisor](https://github.com/CXRunfree/Autovisor/releases)
- 网盘备用: [蓝奏云 · Autovisor-for-windows](https://wwk.lanzouj.com/b05evsxif) 密码: 492l

这是已经打包好的程序, 若需要**源代码**请于 Github 项目主页下载.

#### 五、常见问题

1. 解压后没有 `Autovisor.exe` / 提示缺少依赖文件?

   - 多为杀毒软件误杀: 加入信任区后重新解压; 也请确认下载的是 Releases 里的发行包, 而不是源码.

2. 第一次启动很久没反应 / 依赖下载失败?

   - 首次会检查并下载运行时依赖 (numpy、opencv-python), 等后台日志跑完即可; 下载失败会自动换用 `data/mirrors.json` 里的下一个镜像.
   - 报 `ModuleNotFoundError` / `ImportError: numpy...` 时, 删掉 `packages/` 目录重新运行.

3. 提示 **未检测到有效网址** / 一直**等待登录完成** ?

   - `[course-url]` 要填**课程播放页**的地址 (能直接看到课程视频的页面), 不要填课程首页.
   - 登录页改版导致的等待已在最新版修复, 请先升级到最新发行版.

4. 登录时还是要手动过滑块?

   - 只有 `enableAutoCaptcha = True` 才会自动过滑块, 否则需要手动完成.

5. 只出现命令行窗口, 没有浏览器界面?

   - 命令行是程序后台, 可以查看运行状态; 浏览器加载需要时间, 后台没异常退出就不必担心. 报错通常是浏览器路径配置有误.
   - 找浏览器路径: 打开浏览器, 地址栏输入 `chrome://version`, 其中的"可执行文件目录"就是.

   <p align="left"><img src="resources/markdown/broswer_version.png" width="720" alt="Chrome 可执行文件目录"></p>

6. 看不到浏览器窗口 / 想后台刷课 / 报 `MoveWindow 无效的窗口句柄`?

   - 最小化会让浏览器暂停渲染, 进度不增加, 也会影响弹题检测. 想后台刷课请用 `enableHideWindow = True`, 程序会把窗口移出屏幕.
   - 若报窗口句柄错误, 改回 `enableHideWindow = False`.

7. 卡在加载播放页 / 不会自动跳下一课 / 新版页面刷不了课?

   - 这类基本都是**页面结构还没适配**, 不是配置问题. 目前支持: 智慧共享课、翻转课、融合共享课.

   - 智慧树新版 **AI 课程** (带 AI 角标的课程) 尚未适配, 表现就是识别不到课时、停在加载中或单个视频无限循环; 需要等待适配

     欢迎附上课程链接和日志提 issue.

8. 弹题关不掉 / 程序卡住?

   - 弹题随时可能出现, 而检测不是实时的, 所以无法完全消除; 页面长时间无响应时, 先确认浏览器没有被最小化.

9. 遇到 PPT、PDF 等没有视频的章节会卡住?

   - 目前只处理视频课时, 非视频章节需要手动切到有视频的课时.



#### 六、降低自动化特征

诊断命令 `--check-player <课程链接>` 会只读检查播放器控件结构 (不播放、不下载进度上报、不产生学习记录), 适配新版播放器时先跑它.

以下每一项都在真实浏览器里实测过 (`tests/test_e2e_browser.py`):

| 页面能读到的 | 改动前 | 现在 |
| --- | --- | --- |
| `navigator.webdriver` | `undefined` (stealth 把属性删了) | 原生的 `false` |
| `'webdriver' in navigator` | `false` | `true` |
| `navigator.languages` 等 getter | 被替换, 不是原生函数 | 原生 |
| WebGL 显卡信息 | 写死成 Mac 的 `Intel Iris OpenGL Engine` | 本机真实显卡 |
| `screen` / 视口 | 固定模拟成 1280x720, 会出现视口比窗口还大 | 跟随真实屏幕与窗口 |
| 点击事件 `isTrusted` | 弹窗、协议勾选、融合课弹窗等处为 `false` | 全部为 `true` |
| 点击轨迹 | 一步瞬移到元素正中心, 按下抬起 0 间隔 | 贝塞尔曲线移动, 落点靠中心但有偏差, 按住几十毫秒 |
| 目录滚动 | 协议级滚动, 只有 scroll 没有 wheel | 真实滚轮 |
| 账号密码 | `fill()` 一次写入, 没有按键事件 | 逐字输入 |
| 页面标题 (Windows 隐藏窗口时) | 被改成 `Autovisor - Playwright` | 不改; 仅在标题匹配不唯一时临时换随机串并立即改回 |
| 轮询节拍 | 每 2 秒 / 0.5 秒整 | 以基准值为中心抖动 |
| 倍速 | 写 `video.playbackRate`, 再改写播放器的倍速标签文字 | 点播放器的倍速菜单, 标签由它自己更新 |
| 静音 | 写 `video.volume = 0`, 再给 `.volumeBox` 加 `volumeNone` 伪造图标 | 点播放器的音量按钮, 图标由它自己切换 |
| 起播 / 暂停后恢复 | 调 `video.play()` | 点视频区域 |
| 课中弹题 | 每题固定点"前两个"选项(单选题答案永远落在第二个)、选项间隔 100ms、1 秒多就答完关掉 | 随机选一个、先有读题停顿、点击带轨迹, 小概率才改主意 |

做法:

- 不再注入 `stealth.min.js`. 在有界面的新版浏览器里它弊大于利 (见上表前四行), 改为启动时去掉 `--enable-automation` 并关闭 `AutomationControlled`.
- 页面里的 `el.click()` 全部换成真实输入. 页面脚本派发的事件 `isTrusted` 恒为 `false`, 而且这个属性改不掉.
- 启动后用 CDP 保持页面"前台、活跃": 不进入冻结状态, 空闲检测恒为活跃 (焦点模拟由 Playwright 默认开启).
- 任何一步真实点击走不通 (元素被遮挡、拿不到尺寸), 都会退回 Playwright 原生点击, 不会比原来更容易卡住.

倍速 / 静音 / 起播已经改成点播放器自己的控件 (`modules/player.py`). 控件结构是用 `--check-player` 在真实页面上取到的:

```
.videoArea                      指针移上去控制栏才展开, 平时收起
.volumeBox > .volumeIcon        静音开关
.speedBox  > span               当前倍速标签, 文字形如 "X 1.0"
.speedBox  > .speedList
    .speedTab 'X 1.5' / 'X 1.25' / 'X 1.0'
```

两个实测出来的坑:

- 控制栏默认收起, 而且是靠祖先的 `pointer-events: none` 挡住的——光看元素尺寸看不出来 (`locator.hover()` 会超时). 必须先把指针移到视频区域, 再移到具体控件, 并且落点之后要补一次极小的移动迫使浏览器重新做命中测试; 少了这一步, 倍速菜单会间歇性打不开.
- `.speedTab` 的类名后缀和倍速值对不上 (`speedTab10` 的文字是 `X 1.5` 以外的 `X 1.25`), 所以按标签文字里的数字匹配, 不按类名.

这个播放器只提供 1.0 / 1.25 / 1.5 三档. `limitSpeed` 填菜单里没有的值 (比如 1.8) 时只能退回写属性, 会被页面看到; 填 `0` 则完全不碰倍速, 这也是模板里的新默认值.

每一步真实控件操作走不通时都会退回原来的属性写入, 并在日志的"播放器调节 / 恢复播放"事件里写明用的是哪种方式 (`点菜单` / `写属性`, `点视频区域` / `脚本调用`), 所以退化是看得见的.

课中弹题 (`modules/quiz.py`) 改动前是:

```python
for each in choices[:2]:            # 固定点前两个选项
    await each.click(timeout=500)
    await page.wait_for_timeout(100)
```

问题不在于乱选 (这类弹题本来就是随便选一个关掉), 而在于选得太有规律: 单选题点第一个再点第二个, 答案永远落在第二个选项上, 还产生两次选择事件; 真实日志里弹题出现到关闭只隔 1.6 秒, 没有任何读题时间. 现在改成随机选一个、带 2.5~7 秒读题停顿、点击走指针轨迹, 并且只有约 18% 的概率会"改一次主意". 依旧不尝试答对.

还没处理的:

- 进度回退 (`course_playback.py` 里播放器快于平台记录时的对齐) 仍是设置 `currentTime`.
- 几个提示浮层 (`.exploreTip` 等) 仍是直接从页面里删掉.
- `.answer` 的检查是全页范围的 (弹窗一次只渲染当前题的答案, 所以实际等价于按题判断).

**连接已有 Chrome (`attachExistingChrome = True`)** 是特征最低的方式: 用的是你自己的浏览器和登录态, 没有任何启动参数痕迹. 这个开关在 3.18.x 里只对 `--check-browser` 生效, 正式运行时被忽略 (合并 #149 时丢失), 现已恢复. 连接模式下不会把浏览器 Cookie 写进 `cookies.json`, 结束时只关闭自己打开的标签页, 也不会隐藏你的浏览器窗口.

------
#### 已知问题

- **长时间挂机**有概率弹出人机验证, 程序检测到后会暂停操作, 直到手动验证完成;
- 浏览器窗口若**最小化**可能导致视频播放进度不增加 (页面会变成后台状态);
- 若出现其他异常崩溃, 请提交 issue 并附上报错信息.

#### 写在最后

觉得体验还不错? 请留下你宝贵的 Star ⭐, 并分享给更多有需要的人!

或者为项目发电支持一下~

<p align="left"><img src="resources/markdown/donate.png" width="200" alt="赞赏码"></p>

**作者的 CSDN:** [欢迎关注~](https://blog.csdn.net/Runfreeone)

**声明：本程序只可用于学习和研究计算机原理, 请于 24h 内删除所有存档！**
