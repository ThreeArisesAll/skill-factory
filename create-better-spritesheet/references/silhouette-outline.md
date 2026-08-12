# 确定性剪影外轮廓

仅在目标尺寸静态帧已经批准、项目画法要求外描边、且尚未制作动画时执行。用 Alpha 膨胀生成外描边，同时锁住身份与内部细节。

## 轮廓契约

1. 从艺术规范或邻近生产资源测量目标尺寸的外轮廓宽度与颜色。
2. 用 `工作分辨率半径 = 目标像素半径 × working-scale` 换算脚本参数。
3. 把描边放在角色图层后方，让原母帧的全部不透明像素逐字节一致。
4. 让新增线宽只服务于剪影识别，内部结构线保持原粗细。
5. 从描边后的高分辨率母帧生成动画，使外轮廓与身体变形共享同一像素来源。

颜色和线宽必须来自当前项目契约。没有依据时，先制作静态对比并向用户确认，不使用其他项目的默认风格。

## 执行

使用 fresh 输出目录运行；方形帧也可继续使用 `--frame-size` 简写：

```bash
<python> <skill-dir>/scripts/add_silhouette_outline.py \
  --master <absolute-approved-working-size-mother.png> \
  --output-dir <absolute-fresh-output-directory> \
  --name <character-outline> \
  --frame-width <contract-frame-width> \
  --frame-height <contract-frame-height> \
  --working-scale <working-scale> \
  --outline-radius <contract-working-resolution-radius> \
  --outline-color '<contract-rrggbb>' \
  --safe-margin <contract-safe-margin>
```

脚本要求母帧尺寸精确等于目标尺寸乘工作倍率，输出描边母帧、目标帧、原图对比和指标 JSON，并拒绝覆盖非空目录。

## 验收

1. 检查脚本报告 `opaque interior pixel-identical: True`。
2. 在原生 `1×` 比较原图与描边版，再用棋盘背景 `4×` 定位边缘问题。
3. 确认视觉体量、中心和基线未改变；只允许 Alpha 包围盒因描边向外扩大。
4. 确认四边安全边距满足现场契约。
5. 检查狭窄间隙、肢体、装备和挂件附近没有不自然粘连、锯齿、光晕或透明 RGB 污染。
6. 与邻近生产资源对比线宽、颜色和采样，确认描边属于同一画法。

完成标准：目标帧出现与项目一致且克制的外轮廓，内部实色像素锁定，全部安全边距与透明度检查通过。
