---
title: 文生图 / 图片翻译 / 图生视频（Claude Skill）
id: claude-image-skill
version: 1.0
summary: |
  本技能定义了在本项目中使用 Claude 风格指令（prompt）进行"文生图"（text→image）、"图片翻译"（image translation）和"图生视频"（image→short video）三类任务的标准流程、输入输出、示例与安全注意事项，便于在自动化流水线或人工操作中统一调用和复用。
tags: [image-generation, image-translation, image-to-video, claude]
---

# 文生图 / 图片翻译 / 图生视频（Claude Skill）

## 概述

本 Skill 面向项目内的图像生成与处理任务，提供三条可复用工作流：

- **文生图（Text→Image）**— 从分镜或分段文本生成用于讲解的科普插图
- **图片翻译（Image Translation）**— 将图中英文替换为中文、保持视觉风格与排版
- **图生视频（Image→Video）**— 在保持文本静止与色块稳定的前提下，为插图添加有限动态效果（短时动画）并导出短视频

## 输入输出约定

### 通用输入字段

| 字段 | 说明 | 必填 |
|------|------|------|
| `segment_text` | 当前分镜或字幕片段文本（中文），用于上下文对齐 | 是 |
| `style` | 期望风格标识（如"扁平矢量", "儿童友好"等） | 否（默认：扁平矢量） |
| `seed` | 随机种子以获得可复现结果 | 否 |
| `image` | 输入图片（用于图片翻译或图生视频） | 条件必填 |

### 输出

- **文生图**：生成的图片文件（jpg/png）与用于再现的最终 prompt 文本
- **图片翻译**：翻译后的图片（同分辨率，原比例输出）及翻译文字映射（OCR 原文→译文）
- **图生视频**：5 秒（或可配置）短视频文件（mp4/webm）及对应的动态描述提示

## 工作流步骤

### 1) 文生图（Text→Image）

1. 依据 `segment_text` 与 `style`，生成英文图像 prompt（**注意：prompt 中禁止出现中文**）
2. 可选后处理：合成少量英文标注（<=3 个词），确保文字范围在画面内
3. 送入图像模型（如 Seedream 5.0 Lite），保存输出图片并记录 prompt 与模型参数

### 2) 图片翻译（Image Translation）

1. OCR 提取图片中的英文文本（保持原位置信息和字体近似信息）
2. 生成翻译指令：将英文翻译为中文，保留专有名词与术语
3. 渲染：将翻译后的中文以匹配原视觉风格的方式覆盖原英文（保留颜色、大小、位置、字体效果的近似）
4. 输出：翻译后图片（原比例）并提供 OCR 对照表与修改记录

### 3) 图生视频（Image→Short Video）

1. 生成动态描述（英文输出）。**关键约束**：
   - 所有中文文本必须保持绝对静止、不变形
   - 无光效、无色块大幅变化
   - 相机静止
2. 将静态图与动态描述输入动画引擎，仅添加极其细微的动作（如眨眼、轻微呼吸、植物摆动等），时长默认 5s
3. 导出视频并同时输出用于再现的 prompt 与动画参数

## 风格化预设

为简化调用与保证风格一致性，Skill 内置一组风格化预设：

| 风格key | 英文描述（用于 prompt） |
|---------|------------------------|
| 8bit像素 | 8-bit pixel art 2D style, large chunky pixel blocks, retro game aesthetic, limited color palette |
| 儿童友好 | children's book illustration, cute cartoon style, bright cheerful colors, friendly rounded characters, soft shading |
| 学术专业 | academic presentation style, professional infographic, clear data visualization, modern clean design |
| **扁平矢量**（默认） | flat design illustration, vector art style, thick bold outlines, solid flat colors, minimal shading |
| 科学严谨 | scientific illustration, realistic rendering, detailed accuracy, neutral lighting |

**默认**: `style` = "扁平矢量"

## Prompt 模板

### 文生图模板（英文输出）

```
# Context
{article_summary}
Keywords: {article_keywords}

# Scene
{segment_text}

# Prompt (single-line English)
"Educational infographic about {segment_text}; {composition}; simple, clear shapes; include up to {labels} labels (e.g. 'Microplastics'); pastel or neutral palette; no Chinese characters; keep all text within image boundaries; {style_description}"
```

### 图片翻译模板

```
"This is an educational illustration about '{segment_text}'. Replace the English text in the image with Chinese translations while preserving original style, color, font appearance, and exact text positions. Requirements:
1) Use correct, standard Chinese characters with no garbled text
2) If a technical term cannot be translated, keep the original English
3) Preserve proper nouns and trademarks in English
4) Translation must match the scientific/educational context of '{segment_text}'
5) Keep layout and proportions unchanged; output at original resolution"
```

### 图生视频模板（英文输出）

```
"Subtle animation for static educational image about {segment_text}: gentle natural motions only (e.g., slight swaying of vegetation, slow bobbing of floating objects, minimal eye blinking if characters present). Duration {duration}s, camera fixed, no zoom/pan. CRITICAL: all Chinese text must remain perfectly static and unchanged (position, size, font); no lighting changes; no particle or glow effects; preserve background colors. Keep animation minimal and natural."
```

## 关键约束

### 文生图约束
- **Prompt 必须用英文**，禁止出现中文
- 最多 3 个英文标注词
- 所有文字必须在画面边界内

### 图片翻译约束
- 中文翻译必须标准、无乱码
- 专有名词和商标保留英文
- 布局和比例完全不变
- 输出原分辨率

### 图生视频约束（硬性）
- 所有中文文本**绝对静止**，位置、大小、字体不变
- 无光照变化
- 无粒子或发光效果
- 相机固定，无缩放/平移
- 动画幅度极小、自然

## 模型参数建议

- **文生图模型**：`doubao-seedream-5-0-lite-260128` 或其他，配置 `guidance_scale`、`resolution`、`seed`
- **翻译**：优先使用专业翻译模型+术语白名单，遇不可译术语保留英文
- **动画**：限制造型变化幅度，保持中文文本静止是硬性约束

## 安全与合规

- 禁止生成受版权保护的受限人物肖像或明显可识别真实个人
- 若用户上传含有可识别面孔，必须先获得授权或模糊处理
- 对包含医疗、法律等敏感信息的图像翻译，标注"仅供参考，非专业建议"
- 保留并返回所有来源材料（原图、OCR 结果、翻译映射）以便审计

## 调试与日志

每次调用应记录：
- Input: `segment_text`
- 使用的 prompt（最终文本）
- 模型参数
- 输出文件路径
- 异常或回退策略

---
作者: AI Director Team
