# 📖 AI 小说写作 Agent

一个基于 LLM 的自动小说创作 Agent，支持生成总纲纲、创作人物、生成章节大纲、内容扩写并自动保存。

## 🚀 快速开始

### 1. 克隆&安装
```bash
git clone [repo] 
cd [repo]
pip install -e . 
# requirements.txt里注释了zhipu和火山
```

### 2. 配置 API 密钥
在 config/config2.yaml 中填入LLM API 密钥：
```yaml
llm:
  api_key: "your_api_key_here" 
  # ps:测试时，dpsk和qwen往往需要多对话几轮
```

### 3. demo
```bash
python ./metagpt/test_novel.py
```

![示例图片](./img/author.jpg)