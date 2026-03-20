---
name: seedream-5-lite-image-generation
description: 基于火山方舟Seedream 5.0 Lite模型，通过curl调用Image Generation API实现文生图、图文生图、多图融合、组图生成、联网搜索生图、流式输出等图像创作能力，默认无水印、固定使用doubao-seedream-5-0-lite-260128模型，适配AI Agent自动化图像生成场景
version: 1.0.0
tags: [图像生成, AI绘图, Seedream, curl调用, 火山方舟]
metadata:
  author: Agent Skill Team
  category: 多媒体创作
  default_model: doubao-seedream-5-0-lite-260128
  default_watermark: false
---

# Seedream 5.0 Lite 图像生成技能（Agent专用）

## 技能执行规范（Agent专用）

### 一、核心默认配置（强制固化）

- **模型ID**：固定为 `doubao-seedream-5-0-lite-260128`，禁止随意替换
- **水印配置**：默认 `watermark: false`，不添加AI生成水印
- **请求地址**：固定为 `https://ark.cn-beijing.volces.com/api/v3/images/generations`
- **鉴权方式**：通过请求头携带 `Authorization: Bearer $ARK_API_KEY` 完成身份校验

### 二、前置鉴权要求

调用前需配置环境变量 `ARK_API_KEY`，或直接替换curl指令中的 `$ARK_API_KEY` 为火山方舟平台获取的真实API Key；新用户需先完成API Key申领、模型开通，参考火山方舟快速入门文档。

---

## 场景化CURL调用示例（仅保留curl）

### 1. 基础文生图（纯文本输入单图输出）

**适用场景**：通过文字描述生成单张高清图片，支持自定义分辨率、输出格式

```bash
curl https://ark.cn-beijing.volces.com/api/v3/images/generations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -d '{
    "model": "doubao-seedream-5-0-lite-260128",
    "prompt": "充满活力的特写编辑肖像，模特眼神犀利，头戴雕塑感帽子，色彩拼接丰富，眼部焦点锐利，景深较浅，具有Vogue杂志封面美学风格，中画幅拍摄，工作室强光效果",
    "size": "2K",
    "output_format":"png",
    "watermark": false
}'
```

### 2. 图文生图（单图输入单图输出）

**适用场景**：基于参考图+文字指令，实现图像编辑、风格转换、元素修改等创作

```bash
curl https://ark.cn-beijing.volces.com/api/v3/images/generations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -d '{
    "model": "doubao-seedream-5-0-lite-260128",
    "prompt": "保持模特姿势和液态服装形状不变，将银色金属材质改为透明清水材质，光影从反射改为折射，透出皮肤细节",
    "image": "https://ark-project.tos-cn-beijing.volces.com/doc_image/seedream4_5_imageToimage.png",
    "size": "2K",
    "output_format":"png",
    "watermark": false
}'
```

### 3. 多图融合生图（多图输入单图输出）

**适用场景**：融合多张参考图的风格、元素，生成全新图像（如穿搭融合、风格迁移）

```bash
curl https://ark.cn-beijing.volces.com/api/v3/images/generations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -d '{
    "model": "doubao-seedream-5-0-lite-260128",
    "prompt": "将图1的服装替换为图2的服装，保持人物姿态不变",
    "image": ["https://ark-project.tos-cn-beijing.volces.com/doc_image/seedream4_imagesToimage_1.png", "https://ark-project.tos-cn-beijing.volces.com/doc_image/seedream4_5_imagesToimage_2.png"],
    "sequential_image_generation": "disabled",
    "size": "2K",
    "output_format":"png",
    "watermark": false
}'
```

### 4. 文生组图（多图输出）

**适用场景**：生成内容连贯的组图（如四季插画、分镜漫画），需开启组图参数

```bash
curl https://ark.cn-beijing.volces.com/api/v3/images/generations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -d '{
    "model": "doubao-seedream-5-0-lite-260128",
    "prompt": "生成4张连贯插画，展现同一庭院一角的四季变迁，统一清新治愈风格",
    "size": "2K",
    "sequential_image_generation": "auto",
    "sequential_image_generation_options": {
        "max_images": 4
    },
    "stream": false,
    "output_format":"png",
    "response_format": "url",
    "watermark": false
}'
```

### 5. 联网搜索生图（实时信息融合）

**适用场景**：需实时网络数据的生图场景（如天气预报、实时资讯插画）

```bash
curl https://ark.cn-beijing.volces.com/api/v3/images/generations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -d '{
    "model": "doubao-seedream-5-0-lite-260128",
    "prompt": "制作上海未来5日天气预报扁平化插画，横向排版，清晰展示天气、温度、穿搭建议，风格干净柔和",
    "size": "2048x2048",
    "tools": [
      {
          "type": "web_search"
      }
    ],
    "output_format":"png",
    "response_format": "url",
    "watermark": false
}'
```

### 6. 流式输出组图（快速预览）

**适用场景**：组图生成时开启流式返回，逐张获取生成结果，降低等待时延

```bash
curl https://ark.cn-beijing.volces.com/api/v3/images/generations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -d '{
    "model": "doubao-seedream-5-0-lite-260128",
    "prompt": "参考输入图，生成4张人物插画，分别佩戴墨镜、骑摩托、戴帽子、拿棒棒糖",
    "image": "https://ark-project.tos-cn-beijing.volces.com/doc_image/seedream4_imageToimages_1.png",
    "sequential_image_generation": "auto",
    "sequential_image_generation_options": {
        "max_images": 4
    },
    "size": "2K",
    "stream": true,
    "output_format":"png",
    "watermark": false
}'
```

---

## 关键参数释义（Agent必看）

| 参数 | 说明 | 示例值 |
|------|------|--------|
| `model` | 固定值，禁止修改 | `doubao-seedream-5-0-lite-260128` |
| `prompt` | 图像描述指令，建议不超过300汉字 | 清晰写明主体、行为、环境、风格 |
| `size` | 分辨率 | `2K`, `3K`, `2048x2048` |
| `output_format` | 输出格式 | `png`, `jpeg`（默认png） |
| `watermark` | 水印开关 | `false`（固定不开启） |
| `sequential_image_generation` | 组图开关 | `auto`开启, `disabled`关闭 |
| `stream` | 流式输出 | `true`逐张返回, `false`全部生成后返回 |
| `tools.type` | 联网搜索 | `web_search`（仅5.0 Lite支持） |

---

## 使用限制（Agent执行约束）

- **参考图格式**：jpeg、png、webp等，单图大小≤10MB，总像素≤6000x6000
- **参考图数量**：最多传入14张，生成总数≤15张
- **限流规则**：IPM限流500张/分钟，超出会触发报错
- **数据保存**：生成图片URL仅保留24小时，需及时保存
- **SDK依赖**：确保环境支持curl请求，无额外依赖
