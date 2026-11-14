<a id="top"></a>

<div align="center">

<h1>🎬 vibe video editing</h1>

<p><strong>Edit videos with an agent using natural language, and free yourself from repetitive tasks.</strong></p>

<p><a href="README.md">简体中文</a> · <strong>English</strong></p>

<p><code>Windows x64</code> · <code>Codex Skill</code> · <code>V0.1 Preview</code></p>

<p><a href="#quick-start">Download &amp; install</a> · <a href="#features">Features</a> · <a href="#how-it-works">How it works</a> · <a href="#usage">Examples</a> · <a href="#showcase">Showcase</a></p>

</div>

| Approach | Workflow |
| --- | --- |
| **Traditional editing** | Spend substantial time reviewing and selecting footage, cleaning up speech, working out the edit, and manually editing and exporting revisions. Repetitive operations take time and energy. |
| **Vibe Video Editing** | Give the agent your media and brief, let it produce a first cut, then review the result and describe your changes. The agent handles the editing and exports through each revision. Once you are happy with the result, ask it to save the confirmed editing rules as a reusable style for similar projects. |

**Keep your attention on the content, creative choices, and judgment. Delegate the repetitive operations to the agent.**

Give Codex your footage, script, reference videos, and editing goals. This skill provides a reusable workflow for analysis, planning, editing, captions, audio, and checking the actual deliverables. You can also save editing styles for reuse in similar projects.

This is a **Windows preview**.

*Author's note: Differences in model style and creative capabilities can affect the result, so the same skill may produce very different videos in Codex and DeepSeek Harness (DSH). Editing workflow experiments have so far been conducted only in Codex; other platforms still require adaptation and validation.*

Automated dependency setup and several specialized capabilities still need validation on the target machine. See [Current status](#status).

<a id="who-is-it-for"></a>
## 👥 Who it helps

| Who you are | What it takes off your plate |
| --- | --- |
| Video editors and production professionals | Delegate footage organization, speech cleanup, caption timing, batch processing, and repeated exports to the agent, reducing the time and effort spent on repetitive operations. |
| Clients, brands, and project owners | Describe your video goals and reference style directly to the agent. Once the first cut is ready, ask the agent for revisions directly, without first spending extensive time explaining your ideas to an editor. |
| Creators with an idea | Provide footage and references, then guide production through conversation. The default workflow can be initiated in Codex and executed by background tools without manually operating traditional editing software. |

You still decide what the video should communicate, which material to use, and which version is ready to deliver.

<a id="quick-start"></a>
## 🚀 Download and install

### Option 1: Give Codex the repository link

Copy the URL of this GitHub repository and send it to Codex together with this prompt:

```text
Install the vibe-video-editing skill from the repository I linked.

Read README, SKILL.md, and 安装与外部依赖.md first. Confirm this is a Windows x64 machine.
Install the skill for this Codex environment, detect existing tools, download missing dependencies,
and generate the configuration. Locate software and model paths automatically.
Prepare specialized models only when the editing task needs them.
Run the relevant checks and a short real sample. Report what works and any specific blockers.
```

Codex carries out the setup. You provide the editing goals and media; it discovers and records dependency locations. Detailed setup instructions are in the [dependency guide](安装与外部依赖.md#auto-install) (Chinese).

### Option 2: Download the ZIP first

1. On this repository's GitHub homepage, click the green **Code** button and choose **Download ZIP**.
2. Extract it where you want to keep the skill. Confirm that the folder contains `SKILL.md`.
3. Send the extracted folder path to Codex:

```text
Install the vibe-video-editing skill from this folder:
[paste the extracted folder path]

Follow its setup instructions to prepare dependencies, generate configuration, and verify the installation.
```

Keep the whole skill folder together so its entrypoint can find the modules, scripts, and references.

<details>
<summary>Technical users: inspect and run the basic dependency setup</summary>

With Python 3.11 or newer available, run these commands from the skill root:

```powershell
# Show the download and configuration plan without installing
python scripts/bootstrap.py

# Prepare the basic runtime dependencies
python scripts/bootstrap.py --install

# Check configuration and dependency files
python scripts/runtime_config.py doctor --features base captions
```

These commands prepare runtime dependencies. Codex registers the skill using the current host's installation mechanism. Successful file checks must be followed by a real caption or video sample.

</details>

<a id="inputs"></a>
## 📂 Two folders and a brief

As with vibe coding, describe the result you want and refine it through outputs and feedback. One simple way to organize a project is:

```text
my-video-project/
├─ references/    Videos you like, or your own previous work
└─ media/         Original footage, images, recordings, scripts, and other usable material
```

**References** help the agent analyze shots, pacing, captions, color, and sound. **Media** supplies the material for the current edit. Add the intended use, aspect ratio, approximate duration, and anything that must be preserved. You can also provide file paths directly; you do not need to pre-cut the footage into clips.

For longer recordings with pauses, repeated takes, or irrelevant sections, ask the agent to map the content and mark candidate ranges before selecting and arranging the edit. This reduces the manual work of reviewing and organizing footage segment by segment.

For example: “Use the reference's pacing to make a vertical short from this footage. Get to the point faster, keep the original voice, and preserve my script.”

Review a representative segment, then give feedback on the actual result: “this drags,” “the caption covers the speaker,” or “this shot does not support the narration.” The agent revises the relevant visuals, captions, or audio and works toward the full video.

## 💡 Where this skill comes from

For the current video demonstration, the author used Codex to edit the original recorded speech without manually operating editing software. In a separate sample demonstration, approximately **11 minutes of source footage** became a finished video following the brief; the author recorded a processing time of roughly **half an hour**. This describes one demonstration; actual turnaround depends on the footage, hardware, and requested revisions. The example videos will be added later.

It grew out of repeated editing and revision work: protecting speech sounds when tightening a cut, keeping captions readable, translating a reference video's techniques into the result, reusing accepted visuals during an audio revision, and keeping production assets useful for later revisions.

Those lessons became shared production rules and modules loaded as needed:

- **Start with the current footage and references.** Inspect the actual videos before choosing pacing, captions, or visual treatment.
- **Protect the script and original speech.** Treat the approved script as the content baseline and make cuts around the real delivery.
- **Separate style from tools.** Learn style from the current references while reusing scripts, analysis methods, and delivery checks.
- **Verify the output.** Check actual captions, sound, video, and production assets, and describe the scope of verification.

<a id="features"></a>
## 🧰 What it does

The main workflow coordinates footage, scripts, timelines, [original speech cleanup](references/speech-editing.md), regular captions, mixing, and final checks. It loads the following **seven specialized modules** when needed.

| Capability | Purpose | Details |
| --- | --- | --- |
| Blazerior speech editing tools | Provide word lists, pause candidates, and EDL execution tools for original speech cleanup, alongside the main workflow's Qwen recognition and alignment | [Module](Functional%20Skills/blazerior-videoediting/SKILL.md) |
| Reference analysis | Break down structure, shots, captions, and audio pacing into a timecoded report | [Module](Functional%20Skills/video-sample-analysis/SKILL.md) |
| Local footage search | Find clips by character, action, or visual features, verify candidates, and export selections | [Module](Functional%20Skills/zhao-sucai/SKILL.md) |
| Local [IndexTTS](https://github.com/index-tts/index-tts) voiceover | Generate narration from a script and authorized voice references, then time the edit to the actual audio | [Module](Functional%20Skills/indextts-local/SKILL.md) |
| Remotion text effects | Create keyword emphasis, animated captions, and text treatments | [Module](Functional%20Skills/remotion-flower-text/SKILL.md) |
| Text animation sound effects | Select, audition, align, and mix sounds for text motion | [Module](Functional%20Skills/flower-text-sfx/SKILL.md) |
| Color grading | Correct exposure and white balance, match shots, and handle project-specific LUT / Log / HDR workflows | [Module](Functional%20Skills/video-color-grading/SKILL.md) |

Original speech cleanup reuses the word-list, pause, and EDL editing tools from [blazerior/videoediting-claude-skill](https://github.com/blazerior/videoediting-claude-skill). Credit and thanks to the original author; the bundled tools retain their MIT license and source checksums. Recognition and alignment use this project's Qwen adapter.

Only the capabilities needed for the current request are loaded. Work on a complete video or ask for a single task such as reference analysis, speech cleanup, caption revision, voiceover, or grading. The detailed workflow documents are currently in Chinese.

<a id="how-it-works"></a>
## 🔎 How the agent understands video

The current workflow turns video into **timestamped visual, audio, and text evidence**, which the agent combines with your brief:

1. **Map the media.** FFprobe reads duration, resolution, frame rate, and audio streams. FFmpeg extracts source-timestamped frames for ordered thumbnails and segment review.
2. **Connect the pictures with the speech.** The main agent reviews sampled and neighboring frames, scripts, and transcripts to understand the content, match shots to narration, and analyze a reference's pacing and captions. Dense motion or uncertain sections receive closer inspection; audio conclusions also use the audio track and acoustic checks.
3. **Use local visual assistance when needed.** Long-video search can use Qwen3-VL to screen characters, actions, and visual features. The agent checks candidates against surrounding frames and cut boundaries. Tools record sampling times; the model is not asked to guess timestamps from an image.

Sampling can miss brief actions, and transcription or visual judgments can be wrong. The workflow therefore checks candidate intervals and actual exports, leaving room for human review and revision. See [reference analysis](Functional%20Skills/video-sample-analysis/SKILL.md) and [local retrieval](Functional%20Skills/zhao-sucai/references/local-vision.md) for the implementation workflow (Chinese).

<a id="models"></a>
## 🎙️ Models used for speech and visual assistance

| Model / component | General role | Role in this skill |
| --- | --- | --- |
| [Qwen3-ASR-1.7B](https://github.com/QwenLM/Qwen3-ASR) | Speech recognition: turn recorded speech into text | Supply a transcript for content checks and review of repetitions and false starts. |
| [Qwen3-ForcedAligner-0.6B](https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B) | Align text with audio and return word- or character-level timestamps | Locate spoken content in the source for caption timing and cut-boundary decisions. |
| [Qwen3-VL-8B](https://github.com/QwenLM/Qwen3-VL) (optional) | Understand visible image content | Screen frames during local footage search for characters, actions, and visual features; it does not transcribe speech. |
| [IndexTTS](https://github.com/index-tts/index-tts) (optional) | Synthesize speech from a script and an authorized voice reference | Generate new narration when requested; original-speech editing keeps the recording. |

The main agent makes editorial decisions using the meaning and context. Scripts also examine waveforms, energy, pauses, and possible breaths to flag areas for review. A fluent transcript does not prove the recording has no repetitions. Alignment supplies timing evidence; it does not decide what should be removed or guarantee a correct cut.

Models and weights are prepared separately as needed, subject to compatible hardware and runtimes. See the [speech setup guide](安装与外部依赖.md#speech) (Chinese).

<a id="rendering"></a>
## 🎬 How the final video is made

```text
References + media + brief
           ↓
Visual analysis, speech recognition, and alignment
           ↓
The agent develops an edit plan and timeline
           ↓
Scripts run FFmpeg / Remotion and other required tools
           ↓
Check the video → revise from feedback → export and deliver
```

- **Make the decisions explicit.** The agent plans source ranges, their order, inserted pictures or clips, caption timing, and audio transitions, using a shared frame or timestamp timeline to keep picture and sound aligned.
- **Execute with media tools.** Codex organizes or writes project scripts. FFmpeg handles trimming, scaling, compositing, grading, mixing, and encoding. Remotion renders regular captions, emphasized text, and text motion for composition on the timeline. Complex shots can be produced separately; Blender is optional.
- **Check real outputs.** Review full decoding, frame counts, audio/video durations, caption boundaries, and loudness, together with representative frames and cuts. Deliver the video and any required independent captions, audio stems, source records, and production settings.

You can initiate and revise the default workflow within Codex while background scripts process the media. Additional software, models, or special effects still need their respective runtimes and checks. When only audio changes and the picture remains valid, the workflow reuses the existing video stream to avoid unrelated re-rendering.

<a id="usage"></a>
## ✍️ After installation

Replace the example paths with your own, or provide files and instructions directly in the conversation.

**Edit a video from a reference**

```text
Use $vibe-video-editing.
Footage folder: D:\VideoProjects\demo\media
Script: D:\VideoProjects\demo\script.txt
Reference video: D:\VideoProjects\demo\reference.mp4

Analyze the reference video's pacing, captions, and audio treatment, then edit a video using my footage.
Preserve my script. Propose the edit and create a representative short segment before finishing the full video.
```

**Clean up original speech only**

```text
Use $vibe-video-editing to clean up this recorded speech.
Tighten clearly excessive pauses within phrases and repeated false starts.
Keep natural pauses between sentences and preserve the script.
Check word endings, breaths, and audio/video sync at each cut.
```

**Revise audio only**

```text
The visuals are approved. Adjust only the background music and speech levels, reusing the existing video stream.
```


You can also describe revisions directly: “tighter pacing,” “these captions are crowded,” or “this footage does not support the sentence.” Codex applies the changes to the current project.

## 🎨 Styles and templates

The style library starts empty. Provide reference videos or describe what the current edit needs. A new style is saved to `Styles/` only when you explicitly request it. After a version looks right, ask: “Save the confirmed editing rules as a new style named …”. The agent records reusable pacing, caption, visual, and audio rules. Ask for that style explicitly on a later project, then adapt it to the new footage. This can reduce repeated explanation and revision. Saving a style records rules rather than training a new model; each new video still needs review.

No text animation template library is bundled. Find a suitable public library and give Codex its link to download, check its license, and adapt it, or create the required effects within the current project.

<a id="hardware"></a>
## 💻 Recommended hardware

These are suggested configurations. The minimum configuration has not been validated across the full workflow; actual requirements depend on media resolution, edit complexity, and the local models enabled.

| Component | Minimum (suggested; pending validation) | Recommended | Author's test machine |
| --- | --- | --- | --- |
| Processor | 6 cores / 12 threads | 8 cores / 16 threads or higher | AMD Ryzen 9 9950X3D, 16 cores / 32 threads |
| Memory | 16 GB RAM | 32 GB RAM | 48 GB RAM |
| Graphics | 8 GB VRAM | 16 GB VRAM | AMD Radeon RX 9070, 16 GB VRAM |
| Operating system | Windows; Linux / macOS compatibility pending validation | Windows 11 | Windows 11 25H2 |

**This release currently supports Windows only; automated installation targets Windows x64.** Linux / macOS have not yet been adapted or validated and are outside this release's supported platforms. GPU compatibility with the model runtime matters as well as VRAM capacity; the current Qwen adapter uses compatible NVIDIA CUDA / AMD ROCm environments. The test machine specification does not imply that every specialized capability has passed validation. See [Current status](#status) for the verified scope.

<a id="status"></a>
## 🪟 Requirements and current status

| Item | Current scope |
| --- | --- |
| Operating system | Windows; the bundled portable installer targets x64 |
| Basic tools | Python, FFmpeg / FFprobe, Node.js, Remotion / React, and a rendering browser |
| Models and optional tools | Qwen, [IndexTTS](https://github.com/index-tts/index-tts), vision models, CLAP or Blender, depending on the task |
| Hardware | Basic editing and model inference are checked separately; the current Qwen adapter uses a compatible `cuda:N` GPU backend |
| Configuration | Codex generates machine configuration; delivery choices belong to the current project |

Basic FFmpeg editing, mixing, and ASS-compatible caption export have integration checks. **Fresh-environment automated installation, default Remotion rendering, and specialized model inference still require end-to-end validation.** Optional Blender scenes require separate checks in that runtime.

See the [capability validation details](安装与外部依赖.md#validation) (Chinese). Obtain software, models, fonts, and media under their respective terms. Model weights, media, and runtimes are not bundled.

<a id="showcase"></a>
## 🎞️ Editing showcase

Example videos and production notes will be added later.

<!-- SHOWCASE:START -->
### Cooking example: source and attribution

The example video will be added later.

- **Original footage:** [Cooking with Laura Homemade Pasta](https://commons.wikimedia.org/wiki/File:Cooking_with_Laura_Homemade_Pasta.webm)
- **Original author:** Northampton Community Television
- **License:** [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/)
- **Changes:** This demonstration uses an AI agent to re-edit the source footage, adjust the visuals, and perform post-production.

This example demonstrates the Vibe Video Editing workflow. Copyright in the original video remains with its rights holders. This demonstration does not imply the original author's endorsement of this project.
<!-- SHOWCASE:END -->

## 📚 Documentation and sources

- [Main skill](SKILL.md) · [Function catalog](功能清单.md) · [Style catalog](风格清单.md)
- [Setup and dependencies](安装与外部依赖.md) · [Project preferences](references/project-settings.md)
- [Third-party speech tools and attribution](Functional%20Skills/blazerior-videoediting/README.md)

The README's quick-entry and category navigation structure was inspired by [Awesome GitHub Copilot](https://github.com/github/awesome-copilot). This project's content and installation instructions describe its own workflow.

## 📄 License

The main project currently has **No license** and does not provide a general-purpose usage grant. Third-party tools retain their own licenses and notices; see the bundled [MIT LICENSE](Functional%20Skills/blazerior-videoediting/LICENSE) and the dependency guide.

---

[Back to top](#top) · [简体中文](README.md)
