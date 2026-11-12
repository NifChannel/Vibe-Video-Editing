# 自动配置与运行环境

本版仅支持 Windows，内置便携自动安装限 Windows x64。运行位置由 Codex 检测及安装后生成，不沿用作者机器路径。完整安装流程见 [安装与外部依赖](../安装与外部依赖.md#auto-install)。正常用户只需把仓库链接交给 Codex 并要求安装。

- scripts/bootstrap.py --install 自动准备基础工具和独立 Remotion 运行时（复用宿主 Python，下载 Windows 便携 FFmpeg / Node），写入 runtime.local.json。
- scripts/runtime_config.py show 显示代理自动定位的配置。VIBE_VIDEO_CONFIG 指定配置文件时优先使用该文件，缺少或损坏应报错。
- scripts/runtime_config.py doctor --features base captions 只检查所选能力的文件与声明，不能替代真实短样推理和渲染。
- python scripts/runtime_config.py run-qwen --input <原片> --output-dir <新目录> 使用自动生成的 Python、模型、设备和 FFmpeg 位置，实际执行随包 Qwen 适配器；--dry-run 仅展示调用。
- common.binary 自动读取同一配置的 FFmpeg/FFprobe/Blender 位置；原有工具环境变量可以覆盖。
- 花字模板不属于预装依赖。用户可自行寻找模板库并提供链接，按当前项目安装适配。

稳定版 Qwen 适配器仍保持 FP16 / cuda:N 接口。GPU 选型与支持判断见 [识别依赖](../安装与外部依赖.md#speech)；不把某一厂牌或型号硬编码为必需，不自动回退模型或云端。IndexTTS 使用官方接口，见 [配音依赖](../安装与外部依赖.md#tts)。

自动安装的文件检查不等于在本机完成真实模型推理。发布检查报告应保留本轮真实验证范围，不能沿用作者历史测试作为新用户机器的验收证据。
