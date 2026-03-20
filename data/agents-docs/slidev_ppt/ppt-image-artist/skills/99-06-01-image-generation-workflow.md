# 文生图工作流程

本skill定义了绘图大师的AI图像生成标准流程，确保生成的图像风格统一、质量稳定。

## 概述

绘图大师使用AI图像生成技术为PPT创作配图，遵循"API优先、本地备选"的原则，采用三步工作流程。

## 图像生成原则

### 1. 优先使用API

**首选方式**：使用Moonshot等在线图像生成API
- 优点：质量高、速度快、无需本地算力
- 调用方式：通过工具调用或代码调用API接口

**备选方式**：检查本地模型是否支持文生图
- 如果本地有支持文生图的大模型（如Stable Diffusion等），可作为备选
- 只有在API不可用时才使用本地模型

### 2. 限定风格

所有图像必须从以下两种风格中选择一种：

#### 风格A：8bit像素
```
8-bit pixel art 2D style, large chunky pixel blocks, brick-style aesthetics, 
Kairosoft retro game aesthetic, 2D pixelated graphics, limited color palette, 
nostalgic gaming vibe, chunky pixels, classic arcade style, vibrant colors
```

**适用场景**：
- 游戏相关内容
- 复古/怀旧主题
- 需要活泼有趣氛围的页面
- 技术概念的简化展示

#### 风格B：扁平矢量
```
flat design illustration, vector art style, thick bold black outlines, 
simple rounded shapes, infographic aesthetic, educational explainer video style, 
solid flat colors, no gradients, minimal shading, clean light background
```

**适用场景**：
- 商业/商务演示
- 教育/科普内容
- 流程图、概念图
- 需要专业简洁风格的页面

## 三步工作流程

### 第一步：生成英文Prompt

**任务**：根据内容需求生成符合要求的英文prompt

**要求**：
1. **选择风格**：根据内容主题选择合适的风格（8bit像素或扁平矢量）
2. **添加风格限定**：将选定风格的描述添加到prompt中
3. **英文输出**：整个prompt必须使用英文
4. **限制文字**：如果图像需要包含文字元素，明确要求图中文字为英文（如："with English text labels"）
5. **描述细节**：包含画面内容、构图、色彩、主体描述等

**Prompt模板**：
```
[主体描述], [动作/状态], [环境/背景], [风格描述], [其他细节]
```

**示例**：
- 内容："展示云计算的概念"
- 选择风格：扁平矢量
- 生成Prompt：
  ```
  Cloud computing concept illustration, floating servers connected to a large 
  cloud icon, data streams flowing upward, flat design illustration, vector 
  art style, thick bold black outlines, simple rounded shapes, infographic 
  aesthetic, educational explainer video style, solid flat colors, no gradients, 
  minimal shading, clean light background, with English text labels
  ```

### 第二步：生成英文图像

**任务**：使用选定的工具生成图像

**流程**：
1. **选择工具**：
   - 优先：调用Moonshot图像生成API
   - 备选：检查并使用本地文生图模型
   
2. **设置参数**：
   - 根据需求设置图像尺寸（推荐 16:9 或 4:3 适合幻灯片）
   - 设置生成质量/步数（如有选项）

3. **生成图像**：
   - 使用第一步生成的英文prompt
   - 保存生成的原始图像（英文版）
   - 文件命名建议：`slide_{number}_topic_en.png`

**API调用示例**（Moonshot）：
```python
# 伪代码示例
response = moonshot_client.images.generate(
    model="image-generation-model",
    prompt=english_prompt,  # 第一步生成的英文prompt
    size="1024x576",        # 16:9比例
    quality="high"
)
image_url = response.data[0].url
# 下载并保存
```

### 第三步：翻译图片中的文字

**任务**：将图像中的英文文字翻译为中文

**翻译Prompt**：
```
这是一张关于「{segment_text}」的科普插图。请将图片中的英文文字翻译成中文，保持原文的风格、颜色、字体等视觉效果。其余非文字部分比如元素布局保持不变，原比例输出。

要求：
1. 使用正确规范的中文字，不能出现乱码或错字
2. 如果某些专业术语难以翻译，直接保留原英文
3. 特殊名词、专有名称的需要保留原英文
4. 翻译要符合「{segment_text}」的科普内容语境
5. 保持图片中文字的排版和位置不变
```

**说明**：
- `{segment_text}`：替换为当前内容的主题描述
- 使用图像编辑AI工具或专门的图像翻译工具
- 保存最终中文版图像
- 文件命名建议：`slide_{number}_topic_zh.png`

**翻译示例**：
- 原图文字："Cloud Computing"
- 翻译后："云计算"
- 保留原字体风格、颜色、位置

## 完整示例

### 场景：为"人工智能发展历史"幻灯片配图

**内容主题**：AI从1950年代至今的发展历程

**执行流程**：

#### Step 1: 生成英文Prompt
选择风格：扁平矢量（适合历史时间线展示）

生成Prompt：
```
AI evolution timeline illustration, vintage computer on the left gradually 
transforming into modern AI chip on the right, milestone markers with dates 
(1950s, 1980s, 2010s, 2020s), connecting path with glowing nodes, flat design 
illustration, vector art style, thick bold black outlines, simple rounded shapes, 
infographic aesthetic, educational explainer video style, solid flat colors, 
blue and orange color scheme, no gradients, minimal shading, clean light background,
with English text labels for years and key terms
```

#### Step 2: 生成英文图像
- 使用Moonshot API生成图像
- 保存为：`slide_03_ai_timeline_en.png`

#### Step 3: 翻译文字
使用翻译Prompt：
```
这是一张关于「人工智能发展历史」的科普插图。请将图片中的英文文字翻译成中文...
```

翻译内容：
- "1950s" → "1950年代"
- "Machine Learning" → "机器学习"
- "Deep Learning" → "深度学习"
- "Generative AI" → "生成式AI"

保存为：`slide_03_ai_timeline_zh.png`

## 注意事项

1. **风格一致性**：同一套PPT的图像应使用统一的风格（要么全部8bit，要么全部扁平矢量）

2. **文字处理**：
   - 第一步明确要求图中文字为英文
   - 第三步专门处理文字翻译
   - 保持字体风格一致性

3. **文件管理**：
   - 保留英文原图作为备份
   - 中文版用于最终PPT
   - 按幻灯片编号命名便于管理

4. **质量控制**：
   - 生成后检查图像清晰度
   - 确认文字翻译准确性
   - 验证风格与PPT整体协调

5. **失败处理**：
   - 如果API调用失败，尝试重试或换用本地模型
   - 如果翻译效果不佳，可手动调整或使用其他翻译工具
   - 保留中间文件便于排查问题
