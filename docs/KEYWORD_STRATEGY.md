# 白银期货投资搜索关键词策略

## 策略说明

为了提供全面的白银期货投资建议，搜索关键词不仅包括白银本身，还涵盖了影响白银价格的上下游产业链和相关因素。

## 关键词分类

### 1. 核心关键词
- **中文**：白银、银价、白银期货
- **英文**：silver

### 2. 上游因素（供应端）
- **矿业和开采**：mining（矿业）、mineral（矿产）、commodities（商品）
- **供应链**：supply chain（供应链）、inventory（库存）

### 3. 下游因素（需求端）
- **工业应用**：industrial demand（工业需求）、industrial metals（工业金属）
- **具体应用**：electronics（电子产品）、solar（太阳能）
- **需求**：demand（需求）

### 4. 宏观经济因素
- **通胀和货币政策**：inflation（通胀）、monetary policy（货币政策）、Fed（美联储）
- **汇率和利率**：dollar（美元）、interest rate（利率）
- **经济数据**：economic data（经济数据）

### 5. 市场因素
- **期货市场**：futures（期货）、COMEX
- **价格走势**：price（价格）

### 6. 相关商品
- **贵金属**：precious metals（贵金属）、gold（黄金）
- **工业金属**：copper（铜）、industrial metals（工业金属）

## 配置方式

### 在 `.env` 文件中配置

```env
# 使用默认关键词（已包含上下游和关联因素）
# SEARCH_KEYWORDS=  # 留空使用默认值

# 或自定义关键词（用逗号分隔）
SEARCH_KEYWORDS=白银,silver,银价,白银期货,mining,commodities,inflation,monetary policy,gold,copper,futures,COMEX
```

### 默认关键词列表

程序默认包含以下关键词（可在 `config.py` 中查看完整列表）：

```
白银, silver, 银价, 白银期货, precious metals, 贵金属,
mining, 矿业, 矿产, mineral, commodities, 商品,
industrial demand, 工业需求, electronics, 电子产品, solar, 太阳能,
inflation, 通胀, monetary policy, 货币政策, Fed, 美联储,
dollar, 美元, interest rate, 利率, economic data, 经济数据,
futures, 期货, COMEX, 持仓, inventory, 库存,
gold, 黄金, copper, 铜, industrial metals, 工业金属,
supply chain, 供应链, demand, 需求, price, 价格
```

## 搜索逻辑

程序会在以下内容中搜索关键词：
- 文章标题
- 文章摘要/描述

只要标题或摘要中包含**任意一个**关键词，文章就会被收录。

## 为什么需要扩展关键词？

1. **全面的信息收集**：影响白银价格的因素很多，不仅限于白银本身
2. **上下游分析**：了解供应（矿业）和需求（工业应用）的变化
3. **宏观经济影响**：通胀、货币政策、美元强弱等对白银价格有重大影响
4. **相关商品联动**：黄金、铜等商品价格变化可能影响白银
5. **市场情绪**：期货市场、持仓量等反映市场情绪

## 建议

1. **根据需求调整**：如果只关注特定方面，可以在 `.env` 文件中自定义关键词
2. **使用置信度评估**：由于关键词范围扩大，建议使用置信度评估来筛选高相关性的文章
3. **定期更新**：根据市场变化，可以定期调整关键词列表

## 注意事项

- 关键词范围扩大后，可能会匹配到更多文章
- 建议结合置信度评估（`MIN_CONFIDENCE_SCORE`）来筛选高质量内容
- 如果使用RSS源，某些关键词可能匹配不到文章（因为RSS源是通用财经新闻）
- 使用NewsAPI可以获得更好的关键词匹配效果
