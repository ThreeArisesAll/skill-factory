# 确定性站立待机配方

仅用于正面、全身、脚底落地、方形帧的轻微呼吸待机。其他动作和镜头使用 [motion-design.md](motion-design.md) 中的通用动作流程及适合该动作的生产方法。

## 动作链

- 头部与肩膀承担主要起伏。
- 躯干与髋部用较小幅度连接上下半身。
- 膝部和鞋面递减参与。
- 只锁定鞋底接触带和脚底基线。
- 控制水平质心漂移。

优先读取项目的帧数、节奏、幅度和动作参考。缺失时先询问用户并提示提供待机参考；用户明确授权自主设计后，才可把包含重复闭环帧的 `12` 帧、`500 ms` 循环和约帧高 `3%` 的峰值起伏作为明确标注的临时假设。

## 构建

母帧必须是精确的方形工作画布：

```bash
<python> <skill-dir>/scripts/build_idle_spritesheet.py \
  --master <absolute-transparent-mother-frame> \
  --output-dir <absolute-fresh-output-directory> \
  --name <character-idle> \
  --frame-size <contract-frame-size> \
  --frame-count <contract-frame-count> \
  --working-scale <working-scale-at-least-4> \
  --margin <contract-safe-margin> \
  --amplitude <contract-peak-travel> \
  --loop-duration-ms <contract-loop-duration>
```

使用 `--fit-master` 只做一次规范化。脚本从同一母帧确定性生成所有帧，在预乘 Alpha 中变形，最终只降采样一次，并输出独立帧、横向精灵表和无损预览。

## 验证

```bash
<python> <skill-dir>/scripts/validate_spritesheet.py \
  --sheet <absolute-idle-sheet.png> \
  --frame-size <contract-frame-size> \
  --frame-count <contract-frame-count> \
  --profile idle-planted \
  --require-closed-loop
```

按现场契约覆盖安全边距、位移、质心或接触带阈值。连续查看至少三次循环，拒绝上半身活塞感、下半身冻结、鞋底滑动、身份漂移和首尾跳点。

完成标准：专项机械检查通过，原生尺寸下动作传力自然，脚底接触与闭环方式符合待机契约。
