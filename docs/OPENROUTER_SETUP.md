# OpenRouter API 配置指南

## 为什么使用 OpenRouter？

OpenRouter 是一个统一的 API 平台，提供了多个优点：

1. **更便宜**：通常比直接使用 OpenAI API 更经济
2. **更多选择**：支持 400+ 个模型（OpenAI、Anthropic、Google、Meta 等）
3. **免费选项**：部分模型提供免费使用
4. **兼容性**：完全兼容 OpenAI API 格式，无需大幅修改代码

## 获取 OpenRouter API Key

1. 访问 [OpenRouter 官网](https://openrouter.ai/)
2. 注册账号（可以使用 Google/GitHub 账号快速登录）
3. 访问 [API Keys 页面](https://openrouter.ai/keys)
4. 创建新的 API Key
5. 复制 API Key（格式：`sk-or-v1-...`）

## 配置步骤

### 方式1：使用 OpenRouter（推荐）

在 `.env` 文件中配置：

```env
# 使用OpenRouter（推荐）
OPENROUTER_API_KEY=sk-or-v1-your-openrouter-api-key-here

# 或者指定提供商（可选）
AI_PROVIDER=openrouter
```

### 方式2：继续使用 OpenAI

在 `.env` 文件中配置：

```env
# 使用OpenAI
OPENAI_API_KEY=sk-your-openai-api-key-here

# 或者指定提供商（可选）
AI_PROVIDER=openai
```

### 方式3：优先级自动选择

程序会自动选择：
- 如果配置了 `OPENROUTER_API_KEY`，优先使用 OpenRouter
- 如果只配置了 `OPENAI_API_KEY`，使用 OpenAI
- 如果都没配置，使用默认评估（置信度分数 0.5）

## 可用模型

程序默认使用 `openai/gpt-4o-mini`，但你可以在代码中修改为其他 OpenRouter 支持的模型：

### 推荐模型（性价比高）

- `openai/gpt-4o-mini` - OpenAI 最经济的模型（默认）
- `google/gemini-flash-1.5` - Google 快速模型
- `meta-llama/llama-3.2-3b-instruct:free` - Meta 免费模型
- `qwen/qwen-2.5-7b-instruct:free` - 免费中文模型

### 查看所有可用模型

访问：https://openrouter.ai/models

查看每个模型的：
- 价格（部分免费）
- 性能指标
- 提供商信息

## 修改使用的模型

如果要在代码中修改使用的模型，编辑 `confidence_evaluator.py`：

```python
if self.provider == "openrouter" and Config.OPENROUTER_API_KEY:
    # 修改这里的模型名称
    self.model = "google/gemini-flash-1.5"  # 或其他模型
```

## 成本对比

### OpenAI API
- `gpt-4o-mini`: 输入 $0.15/1M tokens，输出 $0.60/1M tokens
- 每次评估约 $0.0005-0.001

### OpenRouter
- `openai/gpt-4o-mini`: 通常更便宜
- 免费模型：`meta-llama/llama-3.2-3b-instruct:free` 等完全免费

## 优势

1. **成本更低**：OpenRouter 的定价通常更优惠
2. **免费选项**：可以尝试免费的模型
3. **更多选择**：可以轻松切换到其他模型
4. **统一接口**：一个 API 访问多个提供商

## 注意事项

1. **模型名称格式**：OpenRouter 需要使用完整模型名称，如 `openai/gpt-4o-mini`
2. **API Key 格式**：OpenRouter API Key 以 `sk-or-v1-` 开头
3. **兼容性**：代码使用 OpenAI SDK，但通过 `base_url` 指向 OpenRouter，完全兼容
4. **计费方式**：OpenRouter 按 token 计费，部分模型免费

## 故障排除

### 如果遇到认证错误

1. 检查 API Key 是否正确（应该以 `sk-or-v1-` 开头）
2. 确认 API Key 已复制完整
3. 检查 `.env` 文件中的配置是否正确

### 如果遇到模型不存在错误

1. 检查模型名称是否正确（需要包含提供商前缀）
2. 访问 https://openrouter.ai/models 确认模型可用
3. 某些模型可能需要特殊权限或付费

## 相关链接

- OpenRouter 官网：https://openrouter.ai/
- API 文档：https://openrouter.ai/docs
- 模型列表：https://openrouter.ai/models
- API Keys：https://openrouter.ai/keys
