# VidBee AI 自动化工作流 - 快速开始

## 📋 概述

这个自动化流程将视频下载与 AI 内容生成结合：

```
视频下载 → AI 分析 → 生成图片 + 语录 → 输出配对文件
```

## ⚙️ 配置 .env 文件

### 步骤 1: 复制示例文件

```bash
cd python-ai-automation
cp .env.example .env
```

### 步骤 2: 编辑 .env 文件

用你的编辑器打开 `.env` 文件，填入你的 OpenAI API Key：

```env
# OpenAI API 配置
OPENAI_API_KEY=sk-你的API密钥在这里
OPENAI_BASE_URL=https://api.openai.com/v1

# 图片风格配置
IMAGE_STYLE=anime
IMAGE_SIZE=512x512

# 生成器类型 (openai | sd)
GENERATOR_TYPE=openai

# 输出目录
OUTPUT_DIR=output
```

**获取 OpenAI API Key：**
1. 访问 https://platform.openai.com/api-keys
2. 点击 "Create new secret key"
3. 复制密钥并粘贴到 `.env` 文件中

## 🚀 运行示例

### 示例 1: 使用关键词直接生成

```bash
# 安装依赖
pip install -r requirements.txt

# 使用关键词生成 3 张图片和语录
python main.py --keywords 温柔 独立 自信 --count 3
```

**输出：**
```
🔑 Using provided keywords: 温柔, 独立, 自信
📁 Output directory: output\温柔_独立_自信_20260615_164000
🎨 Generating 3 images...
   Generating image 1/3...
   Saved: image_01.png
   Generating image 2/3...
   Saved: image_02.png
   Generating image 3/3...
   Saved: image_03.png
💬 Generating 3 quotes...
   [1] Image: image_01.png
       Quote: 温柔不是软弱，而是选择坚强...
   [2] Image: image_02.png
       Quote: 独立意味着...
   [3] Image: image_03.png
       Quote: 自信是从内心散发...

✅ Complete! Output saved to: output\温柔_独立_自信_20260615_164000
```

### 示例 2: 分析视频文件

```bash
# 分析视频文件并生成配套内容
python main.py --filename "E:\downloads\my_video.mp4" --style anime --count 5
```

### 示例 3: 使用不同风格

```bash
# 写实风格 + 励志语录
python main.py --keywords 奋斗 梦想 --style realistic --quote-style inspirational --count 3

# 浪漫风格
python main.py --keywords 爱情 幸福 --style semi_realistic --quote-style romantic --count 4
```

## 📊 输出文件结构

```
output/
└── 温柔_独立_自信_20260615_164000/
    ├── image_01.png    # AI 生成的图片
    ├── image_02.png
    ├── image_03.png
    ├── quotes.txt      # 语录文本
    ├── pairing.json    # 图片-语录配对数据
    └── video_info.json # 视频元数据（如果从文件分析）
```

## 🎨 可用参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--keywords` | 关键词列表 | 必填（或 --filename） |
| `--filename` | 视频文件路径 | - |
| `--style` | 图片风格：anime / realistic / semi_realistic | anime |
| `--count` | 生成数量 | 3 |
| `--quote-style` | 语录风格：emotional / inspirational / romantic / philosophical | emotional |
| `--output-dir` | 输出目录 | output |

## 💡 完整工作流示例

假设你想为下载的视频自动生成配套内容：

```bash
# 1. 下载视频到 downloads 目录
# （使用 VidBee Desktop 下载）

# 2. 运行自动化处理
cd python-ai-automation
python main.py --filename "E:\downloads\beautiful_sunset.mp4" --style anime --count 3

# 3. 查看输出
# 输出文件在 output/beautiful_sunset_YYYYMMDD_HHMMSS/ 目录