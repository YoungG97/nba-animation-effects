# NBA Player Video Maker: Typography & Shadow Specifications

## 1. 字体选用规范（Broadcast Typography Standard）
- **官方主力英数与通用无衬线字体**：
  - `IBM Plex Sans SC Bold`（优先）
  - 路径：`~/Library/Fonts/IBMPlexSansSC-Bold.otf` 或系统路径
  - **优势**：现代几何无衬线骨架，字体字怀（Counters）开阔、笔画结构规整清爽，高字重下密集笔画（如“星、冠、期、守、阵、第、队”）绝不粘连；
- **大标题冲击力字体（用于 100pt+ 砸地大字）**：
  - `AlibabaPuHuiTi-2-115-Black.otf`（阿里巴巴普惠体 2.0 特黑）
  - 仅用于《每天认识一位NBA球员》、《基本信息》、《职业生涯经历及成就》以及电影海报主标题；
  - 严禁在小字号（< 50pt）正文或密集荣誉中使用特黑体。

---

## 2. 阴影规范（The 1px Contour Shadow Policy）
- **核心原则**：
  - **严禁粗重死黑描边（`stroke_width = 0` on Foreground）**：不得给前景字形添加人工加粗描边外扩，以防字形被粗黑墨水包围；
  - **精准采用 1px 微描边轮廓投影**：
    ```python
    # 正确写法：仅在阴影层添加 1px stroke，前景保持纯粹填充
    d.text((cx + 1, cy + 3), text, font=font, fill=(0, 0, 0, 220), stroke_width=1, stroke_fill=(0, 0, 0, 220))
    d.text((cx, cy), text, font=font, fill=fill_color)
    ```
- **视觉效果**：
  - 阴影在字形边缘微探出 1px，并向下偏移 3px；
  - 无论在亮色背景（球场木地板、蓝幕、白球衣）还是暗色背景（黑金冠军服、暗场）上，文字都具备干净锐利的 3D 浮雕立体感；
  - 彻底杜绝了过度羽化导致的“偏平无阴影”，也杜绝了粗描边导致的“厚重黑糊块”。
