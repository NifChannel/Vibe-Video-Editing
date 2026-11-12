# 用 CLAP 检索本机音效

[LAION CLAP](https://github.com/LAION-AI/CLAP#quick-start) 把文字和音频编码到同一个向量空间。这里的文字输入描述**听起来应该是什么声音**。例如「不到6000块」搭配轻快价格牌，可以搜索 `short bright confirmation chime, soft attack, no speech`，字幕原文保留给事件记录。选声时同时听候选的起音、尾音和它在当前画面里的效果。

1. 使用已配置的独立 Python 环境和配套权重。短音效可用 `laion_clap.CLAP_Module(enable_fusion=False, device="cpu")` 搭配上游推荐的 `630k-audioset-best.pt`，以 `model.load_ckpt(ckpt=本机权重路径)` 加载，随后调用 `model.eval()`。如果库里有长素材，按可用声音的时间段切候选，保留源文件与偏移。音频解码失败时只将该候选转成项目临时的 48 kHz 单声道 WAV 后重试。
2. 对候选文件按稳定顺序用 `model.get_audio_embedding_from_filelist(x=候选路径列表, use_tensor=False)` 批量取得向量。重复项目可缓存向量，缓存键至少区分音效内容或路径、大小及修改时间，另记录权重版本和预处理配置。向量与路径顺序要一致，更新音效或模型时刷新对应缓存。
3. 用 `model.get_text_embedding(声音描述列表, use_tensor=False)` 生成查询向量。将两边的向量逐行 L2 归一化，计算 `文本向量 @ 音频向量.T`。每个花字事件按分数降序取前 3–5 个。对动作不明确的事件，可用相近的两种声音描述分别检索并试听。
4. 用已确认的花字入场与口播片段试听。排序分数只用于筛选候选。最终对点依据是动效的实际帧与声音的实际瞬态。候选过重、过长或遮住人声时，换轻一些的候选，或保留静默。

换机时按 [安装与外部依赖](../../../安装与外部依赖.md#sfx) 准备包、权重和分词器缓存。环境或权重未就绪时，使用本机文件名、类别和试听完成匹配，并在交付记录中注明。
