# 共享操作：按当前工具读取对应小节

目录：环境与边界 / 统一清单 / FFmpeg / 字幕 / Blender / QA。

## 环境与边界

Codex 按[自动环境准备](../安装与外部依赖.md#auto-install)安装并定位工具；脚本从自动生成的配置读取路径，再运行 doctor 和实际短样验证。

Python 3.10+标准库；FFmpeg/ffprobe在PATH或通过FFMPEG_BIN、FFPROBE_BIN指定绝对路径。Blender用BLENDER_BIN。依赖由安装流程准备，这些操作脚本本身不安装运行时，不假定GPU编码器存在。doctor不递归扫描磁盘；找不到时结合项目已有脚本/安装目录定位。

以下命令中的scripts路径相对此Skill；实际执行时使用已安装Skill的绝对脚本路径。项目配置和清单保存在当前视频项目，不在全局Skill中写缓存。已有输出默认拒绝覆盖；确认是本次派生产物时才使用--overwrite。

配乐可以使用用户已提供/指定的音频，或主动寻找的外部免费商用曲目。按[入口约定](../SKILL.md)核实当前视频用途、剪辑与署名要求，将曲名、作者、原始来源链接、许可链接/依据、取得日期及必要署名保存在项目素材来源记录中。授权不明的不用；无合适曲目再告知用户，用户可用 Suno 制作。不运行本机音乐生成/代码作曲流程；以下 mix、循环与响度处理只编辑已取得的音频。

共享脚本处理已渲染镜头与全长音轨，不是包含ASR、图像生成或任意动态图表的全自动剪辑器。分镜内容、字幕校正、来源核对和音乐选择仍由Codex依据风格完成。配置的节奏/密度/mood用于制定分镜；不是FFmpeg自动艺术化参数。

原声口播另按[Qwen F 流程](speech-f-workflow.md)使用随 Skill 保存的 Qwen 识别/对齐适配器和全原录声学候选工具；先用 `scripts/speech_settings.py` 解析本次口播选择，再将节奏依据实际应用于语义/声学剪辑计划。保存配置或转写成功本身不代表口播已剪辑。

网页画面优先使用 OBS 独立浏览器源采集；静态信息卡可在当前项目用 Pillow / SVG 制作。

## 项目配置字段

未点名风格时，根据示例独立创建完整JSON配置，不加载已有风格配置当模板。以下只描述共享脚本接口，不提供审美默认值：

| 字段 | 必需结构与取值 |
|---|---|
| schema_version | 1 |
| video | width/height为正偶数；fps为正数或分数字符串，最高240 |
| rhythm | shot_seconds、intro_shot_seconds、hold_shot_seconds为[min,max]正秒数；voice_speed为0.5–2 |
| transitions | type为所用转场描述；density为none/low/medium/high；duration_seconds非负 |
| subtitles | mode为none/full；font_family字符串；font_size、margin_h、margin_v、outline非负；bold布尔；color为#RRGGBB |
| music | mood为从示例提取的描述；target_lufs为−70至0；ducking布尔。该字段不授权生成音乐 |
| sound_effects | density为none/low/medium/high |
| voice | engine、voice说明本次声音来源；duration_factor为0.1–3 |
| export | target_lufs为−70至−5；true_peak_dbtp为−9至0；loudness_range为1–50 |
| tools | editor为本次使用的剪辑工具 |
| extensions | 对象，可为空；只放本次专用参数并在规范说明用途 |

技术字段结合当前素材填写；节奏、字幕、配色与声音依据用户示例，缺少证据时明确暂定。用 `python scripts/style.py validate --config work/edit-settings.json` 校验，随后交给对应工具消费。

## 统一帧清单

路径相对清单所在目录；视频段需预先统一分辨率、帧率和实际帧数。裁切、调速、动效、叠图、复杂转场先完成并渲染为独立镜头；跨镜头转场如有重叠，要将合成后的帧数计入清单，避免双算。

示例为1920×1080、30fps、4秒；真实任务替换所有示例路径与内容：

```json
{
  "schema_version": 1,
  "fps": 30,
  "width": 1920,
  "height": 1080,
  "clips": [
    {"path":"shots/000.mp4","frames":60,"name":"问题","captions_baked":false},
    {"path":"shots/001.mp4","frames":60,"name":"解释","captions_baked":false}
  ],
  "audio": {
    "mix":"audio/mix.wav",
    "voice":"audio/voice.wav",
    "music":"audio/music.wav",
    "sfx":"audio/sfx.wav"
  },
  "subtitles": [
    {"start":0.2,"end":1.7,"text":"这是显示稿"},
    {"start":2.1,"end":3.7,"text":"不是型号的展开读音稿"}
  ],
  "chapters":[{"frame":0,"name":"开场"},{"frame":60,"name":"解释"}]
}
```

clips.frames为正整数，入点由累计帧推导；fps也支持"30000/1001"。audio.mix必需，其他分轨可省略。subtitles用秒，非空文本、无重叠且不越过总时长；无字幕用[]。已经烧录字幕的片段设captions_baked=true，此时不能再提供文本字幕或--ass。当前共享工程仅线性镜头与音轨，不保留原始特效参数；图表文字要改时需重渲染。

## FFmpeg

```powershell
python scripts/ffmpeg_ops.py doctor
python scripts/ffmpeg_ops.py probe 素材.mp4
python scripts/ffmpeg_ops.py render-clip --input 素材.mp4 --start 12.4 --frames 90 --config work/edit-settings.json --fit cover --output shots/000.mp4
python scripts/ffmpeg_ops.py mix --voice audio/voice.wav --music audio/music.wav --sfx audio/sfx.wav --duration 4 --config work/edit-settings.json --output audio/mix.wav
python scripts/ffmpeg_ops.py export work/manifest.json --ass subtitles.ass --output 成片.mp4
```

render-clip默认无声、libx264；--fit contain完整保留、黑边填充，cover填满并裁切，注意脸/手/图文。--config应用目标尺寸/fps；--speed只调画面，声音需另外atempo并重定时。--filter可追加当前任务已确定的FFmpeg调色等滤镜；不要对不同曝光套固定暖色值。--stabilize为两遍vidstab，需要当前FFmpeg编译包含该滤镜。

mix输入voice与sfx应已排程成全长时间轴，music可循环；应用配置的底乐响度/人声闪避，再两遍loudnorm到export目标。无配乐就省略--music；无音效省略--sfx。真正无音轨项目可先制作静音混音，但不能对全静音跑loudnorm，需跳过mix的响度步骤并在QA说明声音目标不适用。

export要求各镜头编码特征一致，默认重新编码输出、48kHz立体声AAC；会写入清单中的章节；不会推断分镜或自动添加转场。--ass可省略。项目如要片尾淡出，先将淡出做进尾镜头/音轨。

### 仅改声音时复用视频流

仅修改 BGM、音效、人声音量或混音，且画面、烧录字幕、镜头时序与口型同步可沿用时，从已核实的上一版成片直接复制视频流，重做需要修改的音轨，再另存新版本。新混音从项目人声、配乐和音效分轨重建，已有最终混音仅在能完成所需调整时复用。声音剪切、文稿或语速变化影响字幕、画面时序或口型时，按受影响的制作流程重新处理。

先核对新混音与成片的时长和起始偏移。需要的尾音和声音事件应完整覆盖，长度差异先查清原因再决定补静音或修整。封装以既定成片时长为依据，不用 `-shortest` 掩盖音轨过短的问题。以下命令适用于已对齐且等长的单视频轨、单混音轨 MP4；多音轨或内嵌字幕按项目要求逐轨映射。

```powershell
ffmpeg -n -i 'previous.mp4' -i 'new-mix.wav' -map 0:v:0 -map 1:a:0 -map_metadata 0 -map_chapters 0 -c:v copy -c:a aac -b:a 192k -ar 48000 -movflags +faststart 'audio-revision.mp4'
```

从新文件核对视频流内容与上一版一致、帧数和音画时长符合原时间线，并测量编码后的响度与真峰值。抽听声音修改处、衔接和结尾。同步更新分轨与交付记录。

## 字幕

按实际音频人工校对或使用可用的本地ASR/已知文本对齐能力。客户已提供文字口播稿时，以原稿校对识别结果，不借字幕制作修改原稿；录音与文字有差异时记录并沟通。字幕可断行和调整时码，不自动加入澄清、假设或免责提示。画面也不额外添加“示意图”“类比示意”等小字角标；不得将这类说明当作正常图例自动加回。配音读音与显示型号分开，不按平均字数分摊时码。共享脚本负责校验和写文件。

### 普通字幕的默认渲染

1. 复用项目中兼容的 Node.js、React、Remotion 和渲染浏览器。需要查阅专题时直接读取 `remotion-captions`，需要导出时按需读取 `remotion-render`。
2. 用校对后的 `manifest.subtitles` 生成组件输入，将字幕起止时间映射到最终合成的帧率与同一时间轴。以项目基础样式渲染普通字幕，保持字体、颜色和位置一致。确认真实字体加载并保留语义断行，先渲染代表片段检查时码、长句和画面安全区。
3. 可直接在 Remotion 中合成，也可渲染透明字幕层后用 FFmpeg 叠加。核对帧率、帧数和音画同步。字幕已合成进片段时，交给共享导出脚本的清单设置 `captions_baked=true` 并清空 `subtitles`，不再传 `--ass`。保留原时间轴清单，供独立字幕交付和 QA 使用。
4. 如 Remotion 环境无法完成渲染，先检查现有项目运行环境；仍不可用时可用 SRT／ASS 流程交付，并记录实际渲染工具和回退原因。

### 独立字幕与兼容导出

```powershell
python scripts/subtitles.py work/manifest.json --config work/edit-settings.json --srt 字幕.srt --ass 字幕.ass
```

独立字幕可按交付需要输出 SRT 或 ASS。使用 FFmpeg 兼容烧录时传入 ASS 文件。ASS读取font_family、字号、粗体、颜色、描边和边距，按清单分辨率缩放。先确认字体已安装并检查中文/≈/℃字形。Blender文本样式近似ASS，阴影/描边可能不同，需要各看一帧后调整；不要承诺两个引擎像素级一致。

### 防止字幕缺失与机械断句

- 先区分文本真的遗漏、时码不对、显示时间过短，以及画面溢出或遮挡；不把“字幕文件有这句”当作成片已完整显示。以客户定稿核对文字顺序、专名、数字与单位，记录真实录音差异，不擅自改稿。可忽略断行、排版空白和非语义标点做辅助比对，但仍需检查标点、单位符号与实际画面。
- 按句法和口播语义重排，不按固定字数截断；“开源模型”“希尔伯特第六问题”等词组、专名、否定结构、数字与单位保持完整。修复原来被拆散的字幕时，合并原有文本再重新分句，以校对后的词级时间作锚点，不能按字数平均分配时长；换行与换字幕是两个独立决定。
- 用最终采用的字体、字号、描边和输出尺寸测量实际行宽，给左右及上下安全区留余量；超宽时优先语义换行或合理分句，必要时适度调字号，不能删词、强行单行或裁掉文字。ASS 的 `WrapStyle: 2` 不会自动替长行兜底；需要时明确写入 `\N`，并检查字体替换后的真实渲染。
- 检查字幕起止及清晰显示时间。极短字幕优先与相邻语义单元合理合并；必要时取消或缩短淡入淡出，避免整条字幕都处于淡化状态。小幅时码保护不能造成相邻字幕重叠、抢先显示下一句或拖到新对象。
- 字幕和人物小窗放在安全区域并互相避让，同时检查主标题、图表标签、人名、标识和素材底部说明。按当前画面分别调整位置，不把某次项目的像素坐标作为通用默认；需要腾空间时等比收整素材展示区，不能靠覆盖或裁掉重要内容腾位置。
- 导出后抽查最长句、两行句、短字幕、专名和数值、开场标题、镜头交界及素材底部有文字的位置。结合实际渲染核对是否完整可见，不只检查 SRT/ASS 或字体宽度计算。

## Blender

```powershell
& $env:BLENDER_BIN --background --python-exit-code 1 --python scripts/blender_project.py -- --manifest work/manifest.json --config work/edit-settings.json --font "<自动配置中的font_file>" --output 剪辑工程.blend
& $env:BLENDER_BIN --background --python-exit-code 1 --python scripts/blender_project.py -- --verify 剪辑工程.blend --manifest work/manifest.json --report work/blender-check.json --preview work/blender-preview.png --frame 30
```

默认场景Video_Edit；--scene可改名。--base可加载已有三维源文件后添加编辑场景，不复制原项目硬编码路径。Movie在5轨，字幕7轨，mix/voice/music/sfx在1–4轨，只有mix默认开。中文字体显式传入并打包。每段按整数帧定位，媒体相对工程保存；重新打开再看媒体和预览。兼容分支覆盖strips/sequences及TEXT length/frame_end；实际测试版本见建设报告，其他版本需短片验证。

## QA与复现

```powershell
python scripts/qa.py work/manifest.json --video 成片.mp4 --config work/edit-settings.json --report work/qa.json --frames-dir work/qa-frames
python scripts/selftest.py --workdir 临时验证目录
```

qa检查真实镜头规格/帧数、成片解码、帧率/尺寸/音画长度、字幕边界与重叠、AAC后响度。±1LU和真峰值0.15dB为检查容差。机器通过后仍需看字形、安全区、画面语义与听剪口；黑场可能是有意尾幕，不能一概删掉。selftest在新建目录生成小素材，并在副本中测试风格登记，默认不调用付费服务或原项目脚本。
