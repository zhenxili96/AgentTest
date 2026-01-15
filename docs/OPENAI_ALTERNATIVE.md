# OpenAI API替代方案

## 问题说明

程序默认使用OpenAI API进行置信度评估，但OpenAI API需要付费账户。如果你没有付费账户，可以使用以下替代方案。

## 解决方案

### 方案1：不使用AI评估（最简单）

程序已经支持在没有OpenAI API的情况下运行，但所有文章会使用默认置信度分数（0.5）。

**配置步骤：**

1. 创建 `.env` 文件，**不配置OPENAI_API_KEY**（或留空）：
```env
# OpenAI API配置（不配置，使用默认评估）
# OPENAI_API_KEY=

# NewsAPI配置（可选）
# NEWS_API_KEY=

# 其他配置
SEARCH_INTERVAL_MINUTES=30
MAX_ARTICLES_PER_SEARCH=50
MIN_CONFIDENCE_SCORE=0.5  # 降低阈值，因为使用默认分数
```

2. 修改 `config.py`，将OPENAI_API_KEY从必需项改为可选项（程序已支持，只需修改验证逻辑）

**优点：**
- ✅ 完全免费
- ✅ 程序可以正常运行
- ✅ 可以搜索和保存文章

**缺点：**
- ❌ 无法进行AI置信度评估
- ❌ 所有文章的置信度分数都是0.5
- ❌ 无法自动筛选高质量文章

### 方案2：使用OpenAI免费试用

OpenAI提供新用户免费试用额度（通常是$5或更多）。

**步骤：**
1. 访问 https://platform.openai.com/
2. 注册新账号
3. 添加支付方式（但可能不会立即扣费，有免费额度）
4. 获取API密钥
5. 在 `.env` 文件中配置 `OPENAI_API_KEY`

**优点：**
- ✅ 使用官方API，功能完整
- ✅ 有免费试用额度

**缺点：**
- ⚠️ 需要添加支付方式
- ⚠️ 免费额度用完后需要付费

### 方案3：使用免费的本地AI模型（Ollama）

使用Ollama在本地运行开源大语言模型，完全免费。

**步骤：**

1. 安装Ollama：
   - Windows: 下载安装程序 https://ollama.ai/download
   - 或使用: `winget install Ollama.Ollama`

2. 下载模型：
```bash
ollama pull llama3.2  # 或其他模型，如 qwen2.5
```

3. 修改代码使用Ollama API（需要修改confidence_evaluator.py）

**优点：**
- ✅ 完全免费
- ✅ 数据隐私（本地运行）
- ✅ 无使用限制

**缺点：**
- ⚠️ 需要本地运行模型（需要较好的硬件）
- ⚠️ 需要修改代码

### 方案4：使用Bltcy或OpenRouter（推荐，已集成）

程序已经集成了Bltcy和OpenRouter支持，无需修改代码即可使用。

#### 选项A：使用Bltcy（柏拉图AI，推荐国内用户）

**优点：**
- ✅ 无需科学上网，国内可直接访问
- ✅ 价格优惠，比官方API更便宜
- ✅ 兼容OpenAI接口，无需修改代码
- ✅ 支持多种模型（ChatGPT、Claude、Gemini等260+模型）

**配置步骤：**
1. 访问 [Bltcy官网](https://bltcy.cn/) 注册并获取API Key
2. 在 `.env` 文件中配置：
```env
BLTCY_API_KEY=your-bltcy-api-key-here
AI_PROVIDER=bltcy  # 可选，会自动选择
```

详细说明请查看 `docs/BLTCY_SETUP.md`

#### 选项B：使用OpenRouter

**优点：**
- ✅ 更便宜，通常比直接使用OpenAI API更经济
- ✅ 支持400+个模型（OpenAI、Anthropic、Google、Meta等）
- ✅ 有免费选项（部分模型免费）
- ✅ 兼容OpenAI接口，无需修改代码

**配置步骤：**
1. 访问 [OpenRouter官网](https://openrouter.ai/) 注册并获取API Key
2. 在 `.env` 文件中配置：
```env
OPENROUTER_API_KEY=sk-or-v1-your-openrouter-api-key-here
AI_PROVIDER=openrouter  # 可选，会自动选择
```

详细说明请查看 `docs/OPENROUTER_SETUP.md`

### 方案5：使用其他免费/低成本AI API

可以考虑以下替代方案：

1. **Google Gemini API**：有免费配额
2. **Anthropic Claude API**：有免费试用
3. **本地运行的Open WebUI + Ollama**：完全免费
4. **Hugging Face Inference API**：有免费配额

这些都需要修改 `confidence_evaluator.py` 来适配。

### 方案6：简化评估逻辑（基于规则）

不使用AI，使用基于规则的简单评估方法：

- 根据来源可靠性评分（如Reuters、Bloomberg等知名媒体给高分）
- 根据关键词匹配度评分
- 根据文章长度和完整性评分

这种方法需要修改 `confidence_evaluator.py`，实现基于规则的评分逻辑。

## 推荐方案

**如果没有OpenAI账户，推荐：**

1. **国内用户（推荐）**：方案4A（Bltcy）- 无需科学上网，价格优惠，已集成
2. **国外用户（推荐）**：方案4B（OpenRouter）- 有免费选项，价格便宜，已集成
3. **短期使用**：方案1（不使用AI评估）+ 手动筛选文章
4. **长期使用（有硬件）**：方案3（Ollama本地模型）

## 修改代码以支持无OpenAI运行

程序已经支持在没有OpenAI的情况下运行，但需要修改config.py的验证逻辑。

步骤：
1. 将OPENAI_API_KEY从required_keys改为optional_keys
2. 程序会自动使用默认评估（返回0.5分）
3. 可以正常运行，只是置信度评估功能失效

## 当前状态

当前代码已经支持在没有OpenAI API的情况下运行：
- `confidence_evaluator.py` 会检测是否有API密钥
- 如果没有，返回默认置信度分数（0.5）
- 但 `config.py` 的验证会要求OPENAI_API_KEY，需要修改
