---
name: blazerior-videoediting
description: 使用 Blazerior 的词表、停顿与 EDL 工具辅助整理原录口播、解说和采访。由 vibe-video-editing 的原声口播流程调用，或用户明确要求 Blazerior 口播工具时使用；语音识别与对齐沿用主技能 Qwen 适配器。
---

# Blazerior 口播剪辑工具

本模块是社区版对 [blazerior/videoediting-claude-skill](https://github.com/blazerior/videoediting-claude-skill) 所选工具的整合入口，不是上游完整技能副本。第三方原始脚本与 [MIT LICENSE](LICENSE) 保持不变，文件校验见 [provenance.json](provenance.json)。此入口与 module.json 为本项目的适配文件。

## 执行

1. 原录口播整理按[共用口播规范](../../references/speech-editing.md)与[Qwen F 流程](../../references/speech-f-workflow.md)执行。先解析本项目的[口播节奏选择](../../references/speech-rhythm.md)，识别与对齐继续使用主技能 Qwen 适配器。
2. 按[工具说明](README.md)，将本模块 `assets/tools/` 下需要的脚本复制到当前项目的 `tools/`。用同一份非空 `transcript.json` 实际执行 `dump_words.py` 和 `pauses.py`，结合语义、声学证据校对并生成 EDL。未知概率 `p=-1` 不当作低可信错词；停顿候选不等于可删除区间。
3. 视频连同声音重切时，在项目副本中按实际画幅、帧率、调色、缩放与剪口安全范围适配 `build.py`，再运行需要的阶段。仅整理声音时按同一 EDL 使用项目内音频适配器，保留已认可画面。不能因复用工具而自动启用其竖屏、调色、放大、固定响度或字幕方案。
4. 记录实际执行的工具、参数、保留区间及源时间映射；按共用流程检查字头字尾、同期声、字幕与实际导出。原始脚本和校验文件留在本模块，素材、转写、EDL、项目适配副本与渲染输出留在当前项目。

调用模块指当前代理读取并执行规范。仅提供了当前流程需要的三个工具；不安装或启用上游其他转写服务、模板或浏览器渲染路线。
