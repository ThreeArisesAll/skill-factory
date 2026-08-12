# 动作参考搜索

仅在用户明确无法提供动作参考时执行。无需再次请求搜索许可；主动搜索 Pinterest，然后让用户确认候选。

## Pinterest 搜索

使用可用的网页或浏览器工具直接搜索 Pinterest。Pinterest 页面不可访问、要求登录或结果加载不完整时，使用限定 `pinterest.com` 的网页或图片搜索并打开具体 Pin。

从动作契约构造两至四个窄查询，优先使用英文动作术语：

- `<action> animation reference`
- `<action> key poses`
- `<action> cycle contact passing high point`
- `<direction or camera> <action> animation reference`
- `<body type or equipment> <action> motion reference`

把实际动作、方向、镜头、身体类型、装备和 loop 或 one-shot 语义代入查询。不要用宽泛的 `animation` 或 `character movement` 作为唯一查询。

## 清晰度与价值门槛

使用内置 [walk-cycle-reference.png](../assets/walk-cycle-reference.png) 作为筛选基准。优先选择：

- 原生尺寸足以看清关节、接触点和轮廓
- 连续姿势顺序明确，或关键阶段有标签
- 镜头、角色体量、地面线和运动方向稳定
- 四肢无遮挡，近远侧关系和装备弧线可辨
- 包含动作预备、主动作、极值、恢复或完整循环
- 构图简洁，水印、文字和装饰不遮挡动作

拒绝缩略图过小、姿势顺序不明、肢体严重裁切、透视或体量跳变、重复图拼贴、AI 解剖错误，或只展示成品画风而没有动作信息的候选。单张姿势图只能补充一个极值，不能单独证明完整动作。

## 向用户提交候选

提交二至四个最有价值的候选，而不是返回整页搜索结果。每个候选提供：

- 可访问的 Pin 或原始来源链接
- 缩略预览或清楚的内容描述
- 能支持哪些阶段、方向、节奏或事件判断
- 仍然缺失的动作信息

推荐其中一个，并请求用户确认采用哪个参考。用户确认前，只做动作分析和关键姿势计划，不生成完整帧序列。

Pinterest 只用于发现动作参考。尽量打开 Pin 指向的原始来源，记录作者或来源页面；把外部图用于动作、节奏和姿势分析，不复制其角色身份、服装、品牌元素或画风。未经用户要求，不把第三方图片写入仓库或 Skill 资产。

## 内置行走循环参考

`assets/walk-cycle-reference.png` 是用户提供的内置参考，尺寸为 `1145×337`，SHA-256 为 `b85df770ed6528e2c16ba4817752a533af424b9c2fbe11520564484652c191fc`。其外部原始出处尚未确认。

图中用九个侧视姿势展示两个交替半周期：

1. CONTACT
2. RECOIL
3. PASSING
4. HIGH-POINT
5. CONTACT
6. RECOIL
7. PASSING
8. HIGH-POINT
9. CONTACT，重复首个落脚相位以显式闭环

制作行走循环时必须先检查此图。把它用于接触顺序、重心起伏、摆臂反相、迈步弧线和闭环阶段参考；角色身份、身体比例、服装和最终画法继续服从项目参考。

用户无法提供行走参考时，把内置图作为默认可用参考，同时搜索 Pinterest 寻找更匹配目标镜头、身体类型、速度和装备的候选。若搜索没有产生更高价值的结果，说明搜索结论并推荐直接采用内置图。
