<p align="center">
  <img src="https://github.com/user-attachments/assets/d4f48f71-d76e-4ffe-9fb1-0b075d79bf05" alt="forza-painter FH6 logo" width="720">
</p>

<h1 align="center">forza-painter FH6</h1>

<p align="center">
  <strong>把图片转换成 Forza Horizon 6 Vinyl Group 的生成与导入工具。</strong>
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <a href="README.zh-CN.md">中文</a> ·
  <a href="README.ja-JP.md">日本語</a> ·
  <a href="README.ko-KR.md">한국어</a>
</p>

<p align="center">
  <code>v1.6.6</code> · <code>Windows</code> · <code>Forza Horizon 6</code> · <code>GPU/OpenCL</code> · <code>单文件 EXE</code>
</p>

把 PNG/JPG/BMP 图片转换成 Forza Horizon 6 的 Vinyl Group 图层。软件内完成生成、预览和导入，普通用户不需要 Python、`.venv`、批处理文件，也不需要手动填写内存地址。

> **下载 EXE：** 从 [Releases](https://github.com/ShepherdHL/forza-painter-fh6/releases) 下载 `forza-painter-fh6-v1.6.6.exe`，直接运行。

> **画面发糊先看这里：** 优先提高生成页里的 `Random samples / 随机样本`。随机样本数在 **200000 以上** 通常会有明显质变；数值越高越清晰，但生成时间也会明显增加。

> **导入可能需要等待：** v1.4.1 起会依次尝试多套 FH6 模板定位逻辑，最长可能需要 5 分钟。请保持 FH6 停留在 Vinyl Group Editor，不要切换菜单；若仍失败，请导出详细日志。

| 功能 | 说明 |
| --- | --- |
| 生成 JSON | 使用内置 GPU/OpenCL 生成器把图片转换成 geometry JSON。 |
| 图像预览 | 生成前对比预处理滤镜（luma、双边、海报化、赛璐璐等）。 |
| 导入 Final JSON | 导入本应用生成的 geometry JSON（运行文件夹浏览、最佳 final 选择）。 |
| 导入手工 JSON | 导入 FH6 类型码/手工 JSON（方形、圆形、三角形等）。 |
| 导出游戏 JSON | 将 FH6 中打开的贴膜组导出为手工 JSON。 |
| 安全写入 | 写入前自动定位并验证当前可编辑图层表。 |
| 自动更新 | 启动时检查新版本，发现更新时显示更新内容。 |

## 快速开始

1. 从 [Releases](https://github.com/ShepherdHL/forza-painter-fh6/releases) 下载 `forza-painter-fh6-v1.6.6.exe`。
2. 把 EXE 放在普通可写目录里，例如 `Desktop\forza-painter-fh6`。
3. 双击 EXE 启动。导入 FH6 时如果被 Windows 拦截进程访问，请用管理员身份运行 EXE。
4. 在游戏里进入 `Create Vinyl Group` / `Vinyl Group Editor`，加载球形模板并 `Ungroup`。
5. 在软件里生成 JSON，切到 **导入 Final JSON** 页面，填写游戏里显示的真实模板层数后导入。

不要下载 GitHub 自动生成的 `Source code` ZIP，除非你要开发项目。普通用户只需要 `.exe`。

## 效果预览

<table>
  <tr>
    <td align="center" width="50%">
      <img src="docs/screenshots/app-import-preview.png" alt="软件导入页面"><br>
      <strong>软件导入页面</strong>
    </td>
    <td align="center" width="50%">
      <img src="docs/screenshots/fh6-template-ready.png" alt="FH6 模板准备"><br>
      <strong>游戏里准备模板</strong>
    </td>
  </tr>
  <tr>
    <td align="center" width="50%">
      <img src="docs/screenshots/fh6-import-result.png" alt="FH6 导入效果"><br>
      <strong>导入完成效果</strong>
    </td>
    <td align="center" width="50%">
      <img src="docs/screenshots/fh6-car-applied.png" alt="FH6 车身贴图效果"><br>
      <strong>贴到车身效果</strong>
    </td>
  </tr>
</table>

## 生成 JSON

1. 进入 `Generate JSON` 页面。
2. 点击 `Add images`，添加 PNG/JPG/BMP 图片。
3. 选择品质配置。
4. 可选：开启 `Use custom settings`，修改输出层数、分辨率、随机样本和变异样本。
5. 点击底部固定的 `Start generating`。
6. 等待生成完成，右侧会显示预览，底部会显示日志。

生成的文件会保存在原图片旁边，例如 `image.500.json`、`image.1000.json`、`image.3000.json`。

同一张图片可能会生成多个 checkpoint JSON。导入时优先使用层数最高、最接近模板层数的 JSON；例如 3000 层模板应优先导入 `image.3000.json` 或最终 `image.json`。如果把 500 层 JSON 导入 3000 层模板，画面会明显发糊。

| 预设 | 输出层数 | 随机样本 | 用途 |
| --- | ---: | ---: | --- |
| extremely fast | 500 | 30000 | 快速看构图 |
| fast | 1000 | 60000 | 快速出可用稿 |
| balanced | 1800 | 120000 | 默认建议 |
| slow | 2500 | 220000 | 成品质量，开始进入 200k+ 提升区间 |
| super slow | 3000 | 350000 | 最高清晰度，耗时很长 |

## 导入 JSON

### 导入 Final JSON（生成的 geometry）

1. 启动 FH6，并保持 `Vinyl Group Editor` 打开。
2. 加载或创建一个由大量简单 sphere 图层组成的模板。
3. 把模板 `Ungroup`，并记住游戏里显示的真实层数。
4. 打开 **导入 Final JSON**，点击 `Refresh`，选择正在运行的 `forzahorizon6.exe`。
5. 填写游戏里的真实模板层数。
6. 选择生成运行文件夹，或添加 `.json` / 使用生成输出。
7. 点击 **将 Final JSON 导入 FH6**（高级地址通常保持空白）。

### 导入手工 JSON（类型码形状）

1. 使用相同的游戏连接与模板层数。
2. 在 **导入手工 JSON** 中添加手工/类型码 `.json`，查看支持与不支持形状数量。
3. 导入后请在 FH6 中 **保存并重新加载贴膜组**。

### 导出游戏 JSON

1. 在 FH6 中打开要导出的贴膜组，进入 **导出游戏 JSON** 并导出（文件在 `runtime/typecode-export/`）。

FH 需要额外 4 个边界层来正确保存封面和贴车范围。例如：1000 层 JSON 建议使用至少 1004 层模板；3000 层模板实际可导入约 2996 个可绘制图形。

## 必须注意

- 模板必须已经 Ungroup。
- 软件里的层数必须和游戏里的层数完全一致。
- 导入过程中不要切换菜单。
- 如果重启游戏、重新加载模板、改变模板层数，请用新的正确层数重新导入。
- 如果 JSON 比模板小，未使用的模板层会被隐藏。
- 如果 JSON 比模板大，超出的图形会被裁剪。
- 透明 PNG 的透明背景不会作为可见底色导入。

## 运行文件位置

单文件 EXE 会临时解压内部文件，并把正常运行数据放在 EXE 外部。软件启动日志和 `Tools` 页面会显示具体路径。

EXE 旁边可能出现这些外部文件夹：

- `runtime/`：日志、会话数据和临时文件。
- `webui-data/`：本地浏览器/UI 缓存。

关闭软件后可以删除这些文件夹，用于重置本地运行数据。

## 常见问题

- **无法导入 FH6：** 关闭软件，用管理员身份运行 EXE。
- **GPU/OpenCL 报错：** 更新 NVIDIA/AMD/Intel 显卡驱动。内置生成器使用 OpenCL。
- **定位不到模板：** 确认你在 Vinyl Group Editor，模板已经 Ungroup，层数填写完全正确，扫描期间没有切换菜单。
- **导入效果发糊：** 使用更高层数的 JSON，或提高 `Output layers` / `Random samples`。
- **需要排查问题：** 在软件里点击 `Export detailed log`，把导出的日志附到 issue。

## 资源链接

- 导入参考视频：https://www.bilibili.com/video/BV1hG5Z6nENZ
- 内置 GPU 生成器来源/参考：https://github.com/zjl88858/forza-painter-geometrize-gpu
- 完整更新记录：[CHANGELOG.md](CHANGELOG.md)

## 致谢

本项目基于 Forza Painter 工作流衍生而来，并保留上游 MIT 许可声明。

| 个人 / 项目 | 链接 | 贡献 |
| --- | --- | --- |
| the_adawg (AE) | [forza-painter/forza-painter](https://github.com/forza-painter/forza-painter) | 原版 Forza Painter：MIT 许可的 FH 导入流程、内存写入/导入基础，以及几何图形转贴膜方案。 |
| Sam Twidale | [samcodes.co.uk](https://samcodes.co.uk/) | geometrize-lib；上游许可中致谢的几何逼近原始工作。 |
| Michael Fogleman | [fogleman/primitive](https://github.com/fogleman/primitive) | Primitive 库；上游许可中致谢的基于图元的图像逼近方案。 |
| Omar Cornut | [ocornut/imgui](https://github.com/ocornut/imgui) | Dear ImGui；原版 forza-painter 使用的 GUI 框架。 |
| DxBang | [Bang's Forza Color Converter](https://bang.systems/forza-colors/) | 「取色」标签页使用的 Forza H/S/B 颜色转换。 |
| bvzrays | [bvzrays/forza-painter-fh6](https://github.com/bvzrays/forza-painter-fh6) | 面向 FH6 的桌面分支：UI、导入器/定位逻辑、应用打包，以及极限竞速：地平线 6 工作流思路。 |
| Kloudy (heyitshestia) | [kloudys-fh6-painter](https://github.com/heyitshestia/kloudys-fh6-painter) | FH6 贴膜工具分支：启动器流程、风格预设、Luma Prep、Edge Repair、成品检查点浏览、更新流程、发布打包，以及手工/通用导入器工作。 |
| zjl88858 | [forza-painter-geometrize-gpu](https://github.com/zjl88858/forza-painter-geometrize-gpu) | 内置 GPU 生成器所采用的 GPU/OpenCL geometrize 生成器谱系。 |
| LibreHardwareMonitor | [LibreHardwareMonitor/LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) | 「资源监控」标签页的硬件监控后端。 |
| H3XDaemon | [H3XDaemon](https://github.com/H3XDaemon) | 本仓库贡献者。 |
| MaccLochlainn | [MaccLochlainn](https://github.com/MaccLochlainn) | 本仓库贡献者。 |
| ree9622 | [ree9622](https://github.com/ree9622) | 上游历史中的韩语本地化贡献者。 |

完整贡献者列表见 [contributors 页面](https://github.com/ShepherdHL/forza-painter-fh6/graphs/contributors)。

## 更新日志

这里仅保留带版本号的发布记录。用于软件更新弹窗的完整记录见 [CHANGELOG.md](CHANGELOG.md)。

### v1.6.1 / 2026-05-24

- 更新软件版本到 `v1.6.1`；发布文件现在使用 `forza-painter-fh6-v1.6.1.exe`。
- 内置预设默认关闭 `luma_band` 预处理。
- 导入时不再复用 `webui-data` 里的旧 FH6 会话定位数据，写入前会重新定位当前模板。
- JSON 预览改为使用稳定的单一路径渲染，避免不同打包环境下椭圆预览出现拉伸错乱。

### v1.6.0 / 2026-05-24

- 更新软件版本到 `v1.6.0`；发布文件现在使用 `forza-painter-fh6-v1.6.0.exe`。
- 内置 GPU 生成器更新到上游 `canary-26052401`。
- 加入上游 `errorGridSize` 预设参数支持。
- 集成上游透明区域防外溢算法调整。
- 透明图片最底部大椭圆的生成质量得到显著改善。

### v1.5.4 / 2026-05-23

- 修复高分辨率原图、生成器预览 PNG 和 JSON 预览的缩放显示，预览会按当前预览框等比适配，不再拉伸或只显示局部。
- 修复 JSON 预览里 type 16 旋转椭圆的绘制方式，Import 页预览不再把椭圆笔触压扁或错误旋转。

### v1.5.3 / 2026-05-22

- 增加适配单文件 EXE 的自定义预设导入、图片/JSON 列表移除、checkpoint 复用、输出命名修复和 Pillow 预览 fallback。

### v1.5.2 / 2026-05-22

- 增加真正的单文件 EXE，普通用户不再需要 Python、`.venv` 或额外 helper 文件。
- GUI EXE 可用自身的隐藏 helper 模式执行导入和 FH6 内存定位。
- Tools 页面和启动日志会显示外部运行/缓存文件保存位置。

### v1.5.1 / 2026-05-22

- 修复项目 `.venv` 已存在但其中 Python 缺少 `pip` 时的依赖安装失败问题。
- 改进源码包启动脚本的缺文件诊断提示。

### v1.5.0 / 2026-05-22

- 内置 GPU/OpenCL 生成器更新到上游 `canary-26052102`。
- 引入上游 PR #4 的 work-group evaluation 算法，加速 GPU 候选图形评估。
- 增加启动自动更新检查、根目录 `CHANGELOG.md` 和深色桌面 UI。

### v1.4.1 / 2026-05-21

- FH6 模板自动定位会先后尝试 v1.3 和 v1.4 两套扫描方案。
- 增加 RTTI vtable fallback，并拉长自动定位等待预算。

### v1.4.0 / 2026-05-21

- 增加“导出详细日志”按钮，导出内容上限为 50000 字符。
- 改进 FH6 大块可写内存区域的模板自动定位逻辑。

### v1.3.0 / 2026-05-21

- 内置 GPU/OpenCL 生成器更新到上游 `canary-26052101`。
- 引入上游显卡选择修复，并在生成日志中显示选中的 OpenCL 设备。

### v1.2.0 / 2026-05-20

- 内置 GPU/OpenCL 生成器更新到上游 `canary-26052001`。
- 内置预设和自定义生成配置会显式写入 `forceOpaqueShapes = true`。

### v1.1.1 / 2026-05-20

- 增加集中版本号管理，统一窗口标题、命令行和发布包名称。
- 整理仓库目录和发布包脚本。
