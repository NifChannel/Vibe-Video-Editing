<a id="top"></a>

<div align="center">

<h1>🎬 vibe video editing</h1>

<p><strong>用自然语言，从繁琐的重复性工作中解放，和 Agent 一起完成视频剪辑。</strong></p>

<p><strong>简体中文</strong> · <a href="README.en.md">English</a></p>

<p><code>Windows x64</code> · <code>Codex Skill</code> · <code>V0.1 Preview</code></p>

<p><a href="#quick-start">下载安装</a> · <a href="#features">功能</a> · <a href="#how-it-works">工作原理</a> · <a href="#usage">使用示例</a> · <a href="#showcase">剪辑案例</a></p>

</div>

| 方式 | 工作流程 |
| --- | --- |
| **传统剪辑** | 花费大量时间审阅和筛选素材、整理口播、梳理剪辑思路，再手动完成剪辑与反复导出，重复操作占用大量精力。 |
| **Vibe Video Editing** | 把素材和需求交给 Agent，由它完成初版成片；看过实际效果后，直接告诉它如何修改，让 Agent 继续处理剪辑与导出。满意后，还可以让 Agent 将本次确认的剪辑规则总结为可复用风格，供后续同类项目调用。 |

**把精力留给内容、创意和判断，把繁琐的重复操作交给 Agent。**

把素材、稿件、参考视频和想法交给 Codex，让它按一套可复用的流程分析、规划、剪辑、制作字幕、处理声音，并检查实际交付结果。还可以总结风格以便下次在近似的工程中使用。

当前为 **Windows 预览版**。

*作者注：不同模型的风格与创意能力可能影响成片效果，同一个 skill 在 Codex 和 DeepSeek Harness（DSH）中可能产出风格迥异的视频。目前仅在 Codex 中进行过剪辑流程实验；其他平台尚待适配与验证。*

自动依赖安装与部分专项能力仍需在目标机器完成验证，具体范围见[当前状态](#status)。

<a id="who-is-it-for"></a>
## 👥 为谁节省时间

| 你是谁 | 它能帮你减轻什么负担 |
| --- | --- |
| 传统剪辑师、视频工作者 | 把素材梳理、口播整理、字幕时码、批量处理和反复导出交给 Agent 执行，减少重复操作所需的时间与精力。 |
| 甲方、品牌方、需求提出者 | 直接向 Agent 描述视频目标与参考风格。做出初版成片后，也可直接让Agent继续修改。不必先花大量时间与剪辑师交流想法。 |
| 有想法的创作者 | 提供素材和喜欢的样片，用对话推进制作；默认成片流程可在 Codex 中发起并由后台工具执行，无需自己操作传统剪辑软件。 |

你仍然决定想表达什么、采用什么素材，以及哪一版可以交付。

<a id="quick-start"></a>
## 🚀 下载与安装

### 方式一：把仓库链接交给 Codex

复制当前 GitHub 仓库的地址，把链接和下面这段话一起发给 Codex：

```text
请安装这个仓库中的 vibe-video-editing skill。

先阅读 README、SKILL.md 和《安装与外部依赖.md》，确认本机是 Windows x64。
按当前 Codex 环境完成 skill 安装，自动检测已有工具、下载缺少的依赖并生成配置。
不要让我手动寻找软件或模型路径；专项模型按实际任务需要准备。
安装后运行对应检查和短样验证，告诉我哪些功能已可用、哪些仍有具体阻塞。
```

安装流程由 Codex 执行。你主要提供剪辑目标和素材，依赖位置由它检测和记录。详细步骤见[安装与外部依赖](安装与外部依赖.md#auto-install)。

### 方式二：先下载 ZIP，再交给 Codex

1. 在本仓库主页点击绿色 **Code** 按钮，选择 **Download ZIP**。
2. 将 ZIP 解压到你希望保存 skill 的位置，确认文件夹中有 `SKILL.md`。
3. 把解压后的文件夹路径发给 Codex：

```text
请安装这个文件夹里的 vibe-video-editing skill：
【粘贴解压后的文件夹路径】

按它的安装说明自动准备依赖、生成配置并验证。
```

保留整个 skill 文件夹，让主入口能找到功能模块、共享脚本和参考说明。

<details>
<summary>技术用户：查看和执行基础依赖安装命令</summary>

如果已有 Python 3.11 或更新版本，可在 skill 根目录运行：

```powershell
# 查看下载和配置计划，不执行安装
python scripts/bootstrap.py

# 准备基础运行依赖
python scripts/bootstrap.py --install

# 检查配置和依赖文件
python scripts/runtime_config.py doctor --features base captions
```

这些命令负责运行依赖，skill 的登记由 Codex 按当前宿主的安装方式完成。文件检查通过后，还需要实际的字幕或视频短样验证。

</details>

<a id="inputs"></a>
## 📂 两个文件夹，加一段需求

像 vibe coding 一样，把想法告诉 Agent，再通过成品与反馈逐步对齐。可以先这样整理：

```text
我的视频项目/
├─ 样片/      喜欢的参考视频，或自己以前的作品
└─ 素材/      原始视频、图片、录音、文稿及其他可用资料
```

**样片**帮助 Agent 分析镜头、节奏、字幕、配色和声音的做法；**素材**提供这次真正可入片的内容。再告诉它用途、横竖屏、目标时长，以及哪些内容必须保留，就可以开始分析并制作完整初版成片。也可以直接给文件路径，不必把素材预先剪成小片段。

对于包含大量停顿、重复录制或无关片段的长素材，可以先让 Agent 梳理内容、标记候选区间，再按需求筛选和组织成片，减少逐段审阅与整理的手动工作。

例如：“参考样片的节奏，用这些素材做一条竖屏短片。开头更快进入重点，保留原声，不改我的稿件。”

Agent 先完成并检查完整的初版成片，再交给你观看。你可以针对实际效果说“这里拖了”“这句字幕挡住人物”“这个镜头与口播不相关”。Agent 根据反馈修改对应的画面、字幕或声音，再导出修订版，直到你满意。

<a id="features"></a>
## 🧰 能做什么

主流程组织素材、稿件、时间线、[原声口播整理](references/speech-editing.md)、普通字幕、混音和成片检查，再按任务加载以下 **7 个功能模块**。

| 功能 | 用来做什么 | 说明 |
| --- | --- | --- |
| Blazerior 口播剪辑工具 | 提供原声口播整理所需的词表、停顿与 EDL 工具，与主流程的 Qwen 识别及对齐配合使用 | [模块](Functional%20Skills/blazerior-videoediting/SKILL.md) |
| 样片分析 | 拆解结构、镜头、字幕与声音节奏，形成带时间码的参考报告 | [模块](Functional%20Skills/video-sample-analysis/SKILL.md) |
| 本地长视频找素材 | 按角色、动作或视觉特征检索片段，复核后导出独立选段 | [模块](Functional%20Skills/zhao-sucai/SKILL.md) |
| 本地 [IndexTTS](https://github.com/index-tts/index-tts) 配音 | 按文稿与获准参考声音生成旁白，再以实际音频安排剪辑 | [模块](Functional%20Skills/indextts-local/SKILL.md) |
| Remotion 花字 | 制作关键词强调、动态重点字幕和文字效果 | [模块](Functional%20Skills/remotion-flower-text/SKILL.md) |
| 花字音效 | 为文字动效选声、试听、对帧和混音 | [模块](Functional%20Skills/flower-text-sfx/SKILL.md) |
| 调色 | 校正曝光与白平衡，匹配镜头，按项目处理 LUT / Log / HDR | [模块](Functional%20Skills/video-color-grading/SKILL.md) |

原声口播整理复用了 [blazerior/videoediting-claude-skill](https://github.com/blazerior/videoediting-claude-skill) 的词表、停顿与 EDL 剪辑工具，感谢原作者的工作；随包保留其 MIT 许可证与来源校验，识别和对齐使用本项目的 Qwen 适配器。

这里只加载当前需要的功能。可以完成整条视频，也可以只分析样片、整理口播、改字幕、配音或调色。

<a id="how-it-works"></a>
## 🔎 Agent 如何理解视频

当前流程把视频拆成**有时间码的画面、声音和文本线索**，再由 Agent 结合需求作剪辑判断：

1. **先建立素材地图。** FFprobe 读取时长、分辨率、帧率和音轨，FFmpeg 抽取带源时间码的画面，按顺序形成缩略图或分段检查材料。
2. **结合画面和说话内容。** 主 Agent 查看抽帧、相邻画面、稿件与转写，判断这一段在讲什么、哪些镜头支持当句、参考片的节奏与字幕如何组织。密集动效或不确定处加密查看，声音判断结合音轨与声学检查。
3. **需要时调用本地视觉模型。** 长视频找素材可用 Qwen3-VL 检查人物、动作与视觉特征，筛出候选；Agent 再结合前后画面和剪口复核。采样时刻由工具记录，不让模型凭画面猜时间码。

抽样分析可能遗漏短暂动作，转写和视觉判断也可能有误。因此流程要求检查候选区间与实际导出结果，并保留人工审阅和多轮修改的空间。实现细节见[样片分析](Functional%20Skills/video-sample-analysis/SKILL.md)与[本地检索](Functional%20Skills/zhao-sucai/references/local-vision.md)。

<a id="models"></a>
## 🎙️ 口播用了哪些模型

| 模型 / 组件 | 大体负责什么 | 在本 skill 中的作用 |
| --- | --- | --- |
| [Qwen3-ASR-1.7B](https://github.com/QwenLM/Qwen3-ASR) | 语音识别，把录音转成文字 | 给原声口播建立文本线索，供内容校对、重复与误起审查使用。 |
| [Qwen3-ForcedAligner-0.6B](https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B) | 将文本与音频对齐，给出词或字级时间戳 | 帮助定位一句话、一个词在原片中的位置，为字幕时码与剪口提供依据。 |
| [Qwen3-VL-8B](https://github.com/QwenLM/Qwen3-VL)（按需） | 理解图像中的可见内容 | 用于本地长视频检索的画面初判，辅助判断人物、动作和视觉特征；它不负责口播转写。 |
| [IndexTTS](https://github.com/index-tts/index-tts)（按需） | 根据文稿与获准参考声音合成语音 | 需要新旁白时使用；保留原录口播的剪辑任务沿用原声。 |

主 Agent 负责结合语义作取舍。脚本还会检查波形、能量、停顿与疑似呼吸，把可能需要处理的位置交给它复核。ASR 文本通顺不代表录音里没有重复；词级对齐也不会自动决定哪些内容该删，或保证每个剪口都正确。

这些模型与权重按需另行准备，实际运行取决于兼容环境与硬件，详见[语音安装说明](安装与外部依赖.md#speech)。

<a id="rendering"></a>
## 🎬 视频最后如何剪出来

```text
样片 + 素材 + 需求
        ↓
画面分析、语音识别与对齐
        ↓
Agent 制定剪辑计划与时间线
        ↓
脚本调用 FFmpeg / Remotion 等工具实际制作
        ↓
检查成片 → 反馈修改 → 导出与交付
```

- **先把决定写成计划。** Agent 明确保留哪些原片区间、如何排序、哪里插入图片或视频、字幕何时出现，以及声音如何衔接；用统一的帧或时间码维护音画关系。
- **再由工具执行。** Codex 组织或编写项目脚本，FFmpeg 完成裁切、缩放、合成、调色、混音和编码；Remotion 渲染普通字幕、花字与文字动效，再按时间线合成到画面。复杂镜头按需求单独制作，Blender 是可选工具。
- **看真实产物再交付。** 检查完整解码、帧数、音画长度、字幕边界和响度，并复核代表性画面与剪口。交付成片，以及需要的独立字幕、分轨、素材清单和制作配置。

你可以在 Codex 中发起和修改默认成片流程，后台脚本负责实际媒体处理；涉及额外软件、模型或特殊效果时，仍需相应运行环境和验证。只改声音且画面可以沿用时，流程会复用已有视频流，减少无关的重复渲染。

<a id="usage"></a>
## ✍️ 安装以后怎么用

把实际路径替换进提示词，也可以直接在对话中提供文件与要求。

**参考样片剪一条视频**

```text
使用 $vibe-video-editing。
素材目录：D:\VideoProjects\demo\media
稿件：D:\VideoProjects\demo\script.txt
参考视频：D:\VideoProjects\demo\reference.mp4

先分析参考视频的节奏、字幕和声音处理，再用这些素材制作一条视频。
保留我的稿件内容，直接制作完整初版成片，完成必要检查后交给我观看。
我会根据成片提出修改意见，再继续调整并导出修订版。
```

**只整理原声口播**

```text
使用 $vibe-video-editing 整理这段原声口播。
收紧明显多余的句内气口和重复起音，保留自然句间节奏，不改写稿件。
检查每个剪口的字尾、呼吸和音画同步。
```

**只修改声音**

```text
这版画面已经确认，只调整背景音乐和人声音量，复用现有视频流。
```


你也可以直接说明“更紧凑”“字幕太挤”“这里的素材不相关”等修改意图，Codex 再将要求落实到当前项目。

## 🎨 风格与模板

风格库初始为空。提供你喜欢的参考片，或直接描述当前视频的需要；明确说“保存为新风格”后，才把本次经验登记到 `Styles/`。 当一版成片满意后，可以说：“把这次确认的剪辑规则保存为新风格，命名为……”。Agent 会整理节奏、字幕、画面和声音的可复用约定；下次明确点名该风格，再结合新素材调整，减少反复解释同类要求与从零试剪的负担。保存的是规则，不是训练新模型，每条新片仍需检查。

本包不附带花字模板库。你可以自行寻找可用的公开模板库，把链接交给 Codex 下载、检查许可并适配；也可以在当前项目制作新效果。

<a id="hardware"></a>
## 💻 推荐配置

以下为建议配置，其中最低配置尚未完成整套流程验证；实际需求取决于素材分辨率、视频复杂度及启用的本地模型。

| 项目 | 最低配置（建议，待验证） | 推荐配置 | 作者测试设备 |
| --- | --- | --- | --- |
| 处理器 | 6 核 12 线程处理器 | 8 核 16 线程处理器或以上 | AMD Ryzen 9 9950X3D，16 核 32 线程 |
| 内存 | 16 GB RAM | 32 GB RAM | 48 GB RAM |
| 显卡 | 8 GB VRAM | 16 GB VRAM | AMD Radeon RX 9070，16 GB VRAM |
| 操作系统 | Windows；Linux / macOS 兼容性待验证 | Windows 11 | Windows 11 25H2 |

**当前发布版仅支持 Windows，自动安装限 Windows x64。** Linux / macOS 尚未适配与验证，不属于本版可用平台。显存容量之外，还需检查显卡与模型运行后端的兼容性；当前 Qwen 适配器使用兼容的 NVIDIA CUDA / AMD ROCm 环境。测试设备信息不代表所有专项能力均已完成验收，具体范围见[当前状态](#status)。

<a id="status"></a>
## 🪟 环境与当前状态

| 项目 | 当前范围 |
| --- | --- |
| 系统 | Windows；内置便携自动安装限 x64 |
| 基础工具 | Python、FFmpeg / FFprobe、Node.js、Remotion / React 与渲染浏览器 |
| 模型与可选软件 | 按任务准备 Qwen、[IndexTTS](https://github.com/index-tts/index-tts)、视觉模型、CLAP 或 Blender 等 |
| 硬件 | 基础剪辑与模型推理分别检查；当前 Qwen 适配器使用兼容的 `cuda:N` GPU 后端 |
| 配置 | Codex 自动生成机器配置；交付选择保存在当前项目 |

基础 FFmpeg 剪辑、混音、ASS 兼容字幕导出已有集成检查。**全新环境的自动安装、默认 Remotion 渲染和专项模型仍需完成端到端验收**。可选 Blender 场景需在对应运行时另行验证。

完整边界见[能力验证状态](安装与外部依赖.md#validation)。软件、模型、字体与素材按各自条件取得，包内不包含权重、媒体或运行环境。

<a id="showcase"></a>
## 🎞️ 剪辑案例

案例视频与制作说明将在后续补充。

<!-- SHOWCASE:START -->
### 做菜样片：素材来源与署名

案例视频待补充。

- **原始素材：** [Cooking with Laura Homemade Pasta](https://commons.wikimedia.org/wiki/File:Cooking_with_Laura_Homemade_Pasta.webm)
- **原作者：** Northampton Community Television
- **授权协议：** [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/)
- **修改说明：** 本演示使用 AI Agent 对原素材进行了重新剪辑、画面调整及后期制作。

本案例用于展示 Vibe Video Editing 工作流。原始视频版权归原权利人所有，不代表原作者对本项目的认可或背书。
<!-- SHOWCASE:END -->

## 📚 文档与来源

- [主 skill](SKILL.md) · [功能清单](功能清单.md) · [风格清单](风格清单.md)
- [安装与外部依赖](安装与外部依赖.md) · [项目配置](references/project-settings.md)
- [第三方口播工具与来源](Functional%20Skills/blazerior-videoediting/README.md)

首页组织方式参考 [Awesome GitHub Copilot](https://github.com/github/awesome-copilot) 的快速入口与分类导航；本项目的内容与安装方式按自身功能编写。

## 📄 许可

当前主项目选择 **No license**，尚未提供通用使用许可。第三方工具继续遵循其各自的许可证和声明，详见随附 [MIT LICENSE](Functional%20Skills/blazerior-videoediting/LICENSE) 与依赖文档。

---

[返回顶部](#top) · [English](README.en.md)
