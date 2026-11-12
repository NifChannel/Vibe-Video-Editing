# FFmpeg 调色操作

复用本机 FFmpeg/FFprobe。先运行父技能 `scripts/ffmpeg_ops.py doctor`，再用 `ffmpeg -filters` 或 `ffmpeg -h filter=滤镜名` 核对所需能力。以下为 PowerShell 示例，使用项目工作目录和新的输出文件名。

## 探测源片

```powershell
ffprobe -v error -select_streams v:0 -show_streams -of json 'input.mov'
```

读取 `pix_fmt`、`color_primaries`、`color_transfer`、`color_space`、`color_range` 和 `side_data_list`。常见 HLG 和 PQ 标签分别为 `arib-std-b67`、`smpte2084`。源片有 Dolby Vision 时核对基础层格式和交付要求，先验证实际解码结果。范围或矩阵不一致时须转换像素并写正确标签。

## 同帧对照和示波器

以下例子假定输入已经处于已确认的 Rec.709 SDR，左边为校正前，右边为校正后。示例参数用于验证调用，可替换为该镜头实际滤镜链。HDR 或 Log 先建立能正确显示的技术底片，再对照校正或创意色调。选帧要避开转场叠化，检查相邻切换时另取剪口两边的代表帧。

```powershell
$grade = 'eq=contrast=1.03:saturation=1.04'
ffmpeg -n -ss 2 -i 'input-sdr.mp4' -filter_complex "[0:v]split[base][work];[work]${grade}[graded];[base][graded]hstack[out]" -map '[out]' -frames:v 1 -update 1 'compare.png'
ffmpeg -n -ss 2 -i 'input-sdr.mp4' -vf "$grade,format=yuv444p,waveform=mode=column:scale=ire" -frames:v 1 -update 1 'waveform.png'
ffmpeg -n -ss 2 -i 'input-sdr.mp4' -vf "$grade,format=yuv444p,vectorscope=mode=color3" -frames:v 1 -update 1 'vectorscope.png'
ffmpeg -v error -ss 2 -i 'input-sdr.mp4' -vf "$grade,signalstats,metadata=print:file=-" -frames:v 1 -f null -
```

亮度波形中，大片平台且伴随纹理丢失提示裁切。矢量示波器可定位色偏和过饱和，判断白平衡时要结合真实中性区域。统计值需在同位深、同范围和相近内容下比较。不同构图的平均亮度和色度只作排查线索。

## 技术变换和实际输出

- Log 变换用确认适配曲线与色域的 LUT 或项目既有色彩管理。同名 LUT 也要核对输入及输出。FFmpeg 可用 `lut3d=file=grade.cube:interp=tetrahedral`。把 LUT 放在执行目录并用相对路径可避开 Windows 盘符转义。父技能 `render-clip` 在内部临时目录执行，含相对 LUT 路径的链应从实际资源目录直接调用 FFmpeg，或先验证正确转义后的绝对路径。
- 下例适用于标签可靠、已确认要转为 Rec.709 SDR 的 HLG/PQ 输入。用 `zscale` 进入线性浮点空间，经色调映射与色域转换输出 SDR。峰值和算子是试片起点，尤其要看灯光和反光处的纹理。先试短段，再将同一链用于正式渲染。

```powershell
$toSdr = 'zscale=t=linear:npl=100,format=gbrpf32le,tonemap=tonemap=hable,zscale=p=bt709:t=bt709:m=bt709:r=limited:dither=error_diffusion,format=yuv420p'
ffmpeg -n -i 'hdr.mov' -map 0:v:0 -map '0:a?' -vf $toSdr -c:v libx264 -crf 18 -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv -c:a copy 'preview-sdr.mov'
```

- 对已完成技术变换的 SDR 片段，可把验证过的简易校色链传入父技能 `ffmpeg_ops.py render-clip --filter`，再沿用其帧数和时间映射。该入口在缩放和补边后调用滤镜，输出固定为 8 位 `yuv420p`。需要高精度工作流、HDR 交付、技术变换在缩放前执行，或需要让黑边保持原样时，使用符合该顺序的独立滤镜链或原生编辑器。尽量让技术转换与调色在同一次渲染完成。
- 只调色的整段导出沿用源时序与声音，核对帧数、时间戳和音轨。容器兼容时可复制音轨。最终用 FFprobe 检查实际色彩标签及像素格式，并走父技能的完整解码、时长和声音检查。

流程来源 [agentic-color-grader 的单镜头与多镜头流程](https://github.com/perbhat/agentic-color-grader/tree/main/.pi/skills)、[ffmpeg-ops 的 LUT、示波器与色彩管理资料](https://github.com/0xDarkMatter/claude-mods/tree/main/skills/ffmpeg-ops/references)。
