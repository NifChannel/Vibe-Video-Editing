# 项目口播配置

当前发布版的项目配置只保存工程目录和口播节奏选择，成片采用默认 FFmpeg 交付流程。素材、字幕、分轨、剪辑计划和制作源码按实际需要保存在项目中。

Codex 读取当前工程目录下的 video-editing.delivery.json；不存在时使用 default 口播选择，不自动写文件。确认无口播时跳过整理。用户明确要求其他节奏时，由 Codex 生成或更新配置，用户无需手填 JSON。

```json
{
  "schema_version": 2,
  "project_directory": "C:\\VideoProjects\\demo",
  "speech": {"style": "default"}
}
```

speech.style 允许 auto / default / compact / relaxed。工程路径必须是实际存在文件夹的绝对路径。字段、版本或路径无效时明确报错，保留原文件，不静默回退或覆盖。遇到旧格式时，先核对当前需求，再由 Codex 按本版格式重新生成。

读取与解析：

```powershell
python scripts/delivery_config.py --project "本次工程文件夹绝对路径"
python scripts/speech_settings.py --project "本次工程文件夹绝对路径" --speech-present yes --output "本项目/work/speech-settings.json"
```

需要保存选择时，代理使用 delivery_config.read / defaults / write，带上最新读取的 revision。写入保留校验、并发冲突保护和原子替换；不能覆盖唯一素材或其他工程配置。口播具体执行见[口播节奏](speech-rhythm.md)。
