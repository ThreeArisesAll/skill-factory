# Human Reasoning Bridge v2.1124

这是 `human-reasoning` 的第二个主要版本：在原有 100 轮 HUMAN 推理协议之上，新增 **1024 轮规格级迭代**，累计 **1124 轮**。

新版本不再把重点放在“让 AI 的语言看起来像人”，而是处理更本质的问题：

> 人类判断发生在一个会受伤、会疲劳、拥有生活史、关系、价值、承诺和责任的生命体之中；AI 输出发生在一个由模型、上下文、工具、记忆、权限和操作员组成的工程系统之中。二者可以表现相似，却不应据此推断机制、体验、权利或责任相同。

Skill 的目标是建立一座 **认知桥梁**：识别当前任务中真正相关的人类—AI 结构性差异，为每个差异引入证据、工具、人的输入、权限和验证机制，再作出可执行、可更新、责任清晰的判断。

## 主要变化

- 从 `HUMAN` 五步循环升级为 `BRIDGE` 六步循环：
  - **B**ind to human reality：绑定真实的人、处境、身体成本、权力与后果；
  - **R**ecognize asymmetries：识别当前人类与当前 AI 系统之间相关的不对称；
  - **I**mport reality contact：引入来源、数据、传感器、工具、实验、示范和人的证词；
  - **D**eliberate beyond language：不把流畅语言、长解释或自信语气当作正确性；
  - **G**ive judgment and ownership：给出判断，同时保留人的价值所有权、授权和责任；
  - **E**xecute a learning move：采取最小可逆行动，用现实结果更新模型。
- 建立 32 个人类—AI 差异轴与相应补偿控制。
- 强制分离五种不同性质的主张：行为能力、实现机制、功能状态、主观体验、规范/法律地位。
- 明确比较对象不是抽象的“人类”和“AI”，而是某类真实的人与某个真实部署系统。
- 不要求 AI 模仿人的疲劳、偏见、虚荣或情绪反应；改为按比较优势设计混合认知分工。
- 增加提示敏感性、迎合、解释不忠实、记忆来源、长期承诺、权力、同意、责任和纠错机制。
- 增加 32×32 迭代矩阵、32 轴行为用例、反拟人化用例、触发测试与可复核哈希链。

## 安装

解压后进入唯一顶层目录 `human-reasoning/`：

```bash
./scripts/install.sh
```

当前官方 Codex 用户级目录是：

```text
~/.agents/skills/human-reasoning
```

安装器以该目录为单一真实文件源，并创建兼容链接：

```text
~/.codex/skills/human-reasoning -> ~/.agents/skills/human-reasoning
```

安装器会备份同名旧目录，并运行静态验证。若 Codex 未立即显示新版本，重启 Codex。

## 使用

```text
$human-reasoning 重新审视这个产品定位。不要只给优缺点；识别哪些判断依赖人的真实处境，哪些可以交给 AI，并给出最终选择、责任边界和最小验证实验。
```

```text
$human-reasoning 比较人类教师与 AI 教师的本质差异。不要泛谈“情感”和“效率”，请指定真实部署系统，并为每个相关差异设计补偿控制。
```

```text
$human-reasoning 分析这场创始人冲突。严格区分行为事实、心理假设、权力关系、价值冲突和可验证步骤。
```

```text
$human-reasoning 设计一个由人类、AI Agent、供应商和资金组成的临时公司协议。明确目标所有者、授权、撤销、审计、申诉和后果承担者。
```

## 1024 轮迭代的真实含义

新增轮次采用 **32 个差异轴 × 32 个改进通道** 的正交矩阵：

- 每个差异轴都会经历边界定义、系统范围、人类差异、AI 架构差异、触发条件、证据、现实接触、因果机制、反事实、权力、价值、责任、记忆、校准、提示稳定性、行为测试与最小化等 32 次独立修改；
- 每轮包含一个主要缺陷、一个实际变更、一个验收条件和目标文件；
- 原 v1.100 的前 100 个记录与哈希保持不变；第 101 轮从原最终哈希继续链接；
- 新增 1024 轮是 **可审计的规格迭代**，不是声称进行了 1024 次独立外部模型实验。

完整方法见：

```text
iterations/METHOD.md
iterations/ITERATION-MAP.md
iterations/ITERATION-LOG.md
iterations/iteration-log.json
iterations/rounds/
```

最终迭代链哈希：

```text
85564233f6c04f1fa508b03366d19e33fe8f5dc6e70802ec4196d7fd62ab232c
```

## 验证

```bash
python3 scripts/doctor.py
python3 scripts/run_static_evals.py
python3 scripts/verify_iterations.py
```

这些命令验证包结构、主 Skill 预算、32 轴矩阵、32×32 覆盖、1124 轮链、轮次文件、测试定义和 SHA-256 校验和。真实模型行为仍需在目标 Codex / ChatGPT 宿主中运行 `evals/`，不能由静态检查冒充。

## 目录

```text
human-reasoning/
├── SKILL.md
├── README.md
├── RELEASE-NOTES.md
├── SECURITY.md
├── VERSION
├── agents/openai.yaml
├── assets/AGENTS-snippet.md
├── references/
├── tests/
├── evals/
├── iterations/
└── scripts/
```

## 卸载

```bash
./scripts/uninstall.sh
```

卸载会将已安装目录移动到可恢复备份，不会直接销毁。
