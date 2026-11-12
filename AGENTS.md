# vibe video editing 维护

- 本版只支持 Windows，内置自动安装限 Windows x64；其他系统不执行安装或下载依赖。
- 主项目选择 No license，不擅自添加其他主项目许可；保留随包第三方许可证、来源和文件校验。
- 主入口负责共用制作流程；功能模块在 Functional Skills/<id>。仅用户明确要求保存风格时，在 Styles/<id> 新增子 skill；初始 Styles 为空。
- 安装依赖按[统一依赖入口](安装与外部依赖.md)由 Codex 检测、下载、配置和验证，不要求用户手填依赖路径。运行时和模型保存在用户数据目录，机器配置不提交。
- module.json 维护模块元信息，SKILL.md 维护执行规范。变更后运行 scripts/library.py sync、scripts/library.py validate、scripts/style.py validate 和受影响功能检查。
- 新增依赖或配置键，同步安装文档、assets/runtime.example.json 及实际解析器。未实测能力保留明确状态，不以文件存在或配置通过代替实际推理、渲染或编辑器验收。
- 项目素材、客户稿件、音色、参考文件和测试产物不写入 skill。通用规则与项目选择分别维护，按当前用户明确要求执行。
- 模块调用指当前代理读取并执行其规范。仓库提交与发布依当前宿主规则和用户要求处理。
