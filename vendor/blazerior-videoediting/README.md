# 第三方口播工具

来源：[blazerior/videoediting-claude-skill](https://github.com/blazerior/videoediting-claude-skill)。保留上游 MIT LICENSE；所选原始工具的来源和 SHA256 见 provenance.json。

| 工具 | 用途 |
| --- | --- |
| assets/tools/dump_words.py | 从 segments[].words[] 列出词、时码和置信度，供校对；未知置信度不当作高置信度 |
| assets/tools/pauses.py | 从同一转写列出词间空档，只作剪辑决策的导航 |
| assets/tools/build.py | 在需要视频重切时按项目 EDL 执行；调用前在项目副本适配视觉参数 |

将需要的脚本复制到项目 tools。词表与停顿工具接收当前项目 transcript.json；空转写先排查。build.py 以 tools 的上一级为项目根目录，读取项目生成的 edl.json，其中 source 为原片路径，segments 为保留区间的 start / end 秒数。使用 base 阶段时，先按本次项目设置 W / H / FPS / GRADE 等参数并试渲染。

默认识别与对齐使用主 skill 的 Qwen 适配器，声音整理与原片映射按主流程执行。不要直接运行第三方工具覆盖唯一原片或已有交付。
