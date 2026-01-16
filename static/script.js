// API基础URL
const API_BASE = '/api';

// 标签页切换
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const tabId = btn.getAttribute('data-tab');
        switchTab(tabId);
    });
});

function switchTab(tabId) {
    // 更新按钮状态
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelector(`[data-tab="${tabId}"]`).classList.add('active');
    
    // 更新内容显示
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.getElementById(`${tabId}-tab`).classList.add('active');
    
    // 根据标签页加载数据
    if (tabId === 'articles') {
        loadArticles();
    } else if (tabId === 'keywords') {
        loadKeywords();
    } else if (tabId === 'stocks') {
        loadStocks();
    } else if (tabId === 'stats') {
        loadStats();
    } else if (tabId === 'workflow') {
        refreshWorkflow();
    } else if (tabId === 'recommendation') {
        loadLatestRecommendation();
    }
}

// 数据源类型切换
document.getElementById('source-type').addEventListener('change', (e) => {
    const sourceType = e.target.value;
    const articlesOptions = document.querySelectorAll('#articles-options');
    const trendsOptions = document.getElementById('trends-options');
    
    if (sourceType === 'articles') {
        articlesOptions.forEach(el => el.style.display = 'block');
        trendsOptions.style.display = 'none';
    } else {
        articlesOptions.forEach(el => el.style.display = 'none');
        trendsOptions.style.display = 'block';
    }
});

// 挖掘关键词
async function mineKeywords() {
    const sourceType = document.getElementById('source-type').value;
    const resultArea = document.getElementById('mine-result');
    const btn = event.target;
    
    // 准备数据
    const data = {
        source: sourceType,
    };
    
    if (sourceType === 'articles') {
        data.hours = parseInt(document.getElementById('hours').value);
        data.min_confidence = parseFloat(document.getElementById('min-confidence').value);
        data.limit = parseInt(document.getElementById('limit').value);
    } else {
        const context = document.getElementById('market-context').value;
        if (context) {
            data.market_context = context;
        }
    }
    
    // 显示加载状态
    btn.disabled = true;
    btn.textContent = '挖掘中...';
    resultArea.className = 'result-area loading';
    resultArea.style.display = 'block';
    resultArea.textContent = '正在分析数据并挖掘关键词';
    
    try {
        const response = await fetch(`${API_BASE}/keywords/mine`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        });
        
        const result = await response.json();
        
        if (result.success) {
            resultArea.className = 'result-area success';
            resultArea.innerHTML = `
                <h3>✅ 挖掘成功！</h3>
                <p>共挖掘到 <strong>${result.mined}</strong> 个关键词，成功保存 <strong>${result.saved}</strong> 个</p>
                ${result.keywords && result.keywords.length > 0 ? `
                    <div style="margin-top: 15px;">
                        <h4>关键词列表：</h4>
                        <ul style="margin-top: 10px; padding-left: 20px;">
                            ${result.keywords.slice(0, 10).map(kw => `
                                <li><strong>${escapeHtml(kw.keyword)}</strong> 
                                (相关性: ${kw.relevance_score.toFixed(2)}, 
                                影响: ${kw.impact || '未知'})</li>
                            `).join('')}
                        </ul>
                        ${result.keywords.length > 10 ? `<p style="margin-top: 10px; color: #666;">... 还有 ${result.keywords.length - 10} 个关键词</p>` : ''}
                    </div>
                ` : ''}
            `;
        } else {
            throw new Error(result.error || '挖掘失败');
        }
    } catch (error) {
        resultArea.className = 'result-area error';
        resultArea.innerHTML = `<h3>❌ 挖掘失败</h3><p>${escapeHtml(error.message)}</p>`;
    } finally {
        btn.disabled = false;
        btn.textContent = '开始挖掘';
    }
}

// 加载关键词列表
async function loadKeywords() {
    const keywordsList = document.getElementById('keywords-list');
    keywordsList.innerHTML = '<div class="loading">加载中</div>';
    
    const active = document.getElementById('filter-active').value;
    const minRelevance = parseFloat(document.getElementById('filter-relevance').value);
    const limit = parseInt(document.getElementById('filter-limit').value);
    
    const params = new URLSearchParams();
    if (active) params.append('active', active);
    if (minRelevance) params.append('min_relevance', minRelevance);
    if (limit) params.append('limit', limit);
    
    try {
        const response = await fetch(`${API_BASE}/keywords?${params.toString()}`);
        const result = await response.json();
        
        if (result.success) {
            if (result.keywords.length === 0) {
                keywordsList.innerHTML = '<div class="result-area" style="display: block; background: #fff3cd; border: 1px solid #ffeaa7; color: #856404;">暂无关键词数据</div>';
                return;
            }
            
            keywordsList.innerHTML = result.keywords.map(kw => `
                <div class="keyword-item">
                    <div class="keyword-header">
                        <span class="keyword-title">${escapeHtml(kw.keyword)}</span>
                        <span class="keyword-score">${kw.relevance_score.toFixed(2)}</span>
                    </div>
                    <div class="keyword-meta">
                        <span>
                            <strong>影响方向：</strong>
                            <span class="impact-badge impact-${getImpactClass(kw.impact)}">
                                ${kw.impact || '未知'}
                            </span>
                        </span>
                        <span><strong>来源：</strong>${escapeHtml(kw.source || '未知')}</span>
                        <span><strong>使用次数：</strong>${kw.usage_count || 0}</span>
                        <span><strong>挖掘时间：</strong>${formatDate(kw.mined_at)}</span>
                        <span><strong>状态：</strong>${kw.is_active ? '✅ 活跃' : '❌ 非活跃'}</span>
                    </div>
                    ${kw.reasoning ? `
                        <div class="keyword-reasoning">
                            <strong>分析说明：</strong>${escapeHtml(kw.reasoning)}
                        </div>
                    ` : ''}
                </div>
            `).join('');
        } else {
            throw new Error(result.error || '加载失败');
        }
    } catch (error) {
        keywordsList.innerHTML = `<div class="result-area error" style="display: block;">
            <h3>❌ 加载失败</h3><p>${escapeHtml(error.message)}</p>
        </div>`;
    }
}

// 分析关键词
async function analyzeKeyword() {
    const keyword = document.getElementById('analyze-keyword').value.trim();
    const context = document.getElementById('analyze-context').value.trim();
    const resultArea = document.getElementById('analyze-result');
    const btn = event.target;
    
    if (!keyword) {
        resultArea.className = 'result-area error';
        resultArea.style.display = 'block';
        resultArea.innerHTML = '<h3>❌ 请输入关键词</h3>';
        return;
    }
    
    btn.disabled = true;
    btn.textContent = '分析中...';
    resultArea.className = 'result-area loading';
    resultArea.style.display = 'block';
    resultArea.textContent = '正在分析关键词相关性';
    
    try {
        const data = { keyword };
        if (context) {
            data.context = context;
        }
        
        const response = await fetch(`${API_BASE}/keywords/analyze`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        });
        
        const result = await response.json();
        
        if (result.success) {
            const analysis = result.analysis;
            resultArea.className = 'result-area success';
            resultArea.innerHTML = `
                <h3>✅ 分析完成</h3>
                <div style="margin-top: 15px;">
                    <div style="margin-bottom: 15px;">
                        <strong>关键词：</strong>${escapeHtml(analysis.keyword)}<br>
                        <strong>相关性分数：</strong><span style="font-size: 1.5em; font-weight: 600; color: #667eea;">${analysis.relevance_score.toFixed(2)}</span><br>
                        <strong>影响方向：</strong>
                        <span class="impact-badge impact-${getImpactClass(analysis.impact)}" style="margin-left: 5px;">
                            ${analysis.impact || '未知'}
                        </span>
                    </div>
                    <div class="keyword-reasoning">
                        <strong>分析说明：</strong><br>
                        ${escapeHtml(analysis.reasoning || '无详细说明')}
                    </div>
                </div>
            `;
        } else {
            throw new Error(result.error || '分析失败');
        }
    } catch (error) {
        resultArea.className = 'result-area error';
        resultArea.innerHTML = `<h3>❌ 分析失败</h3><p>${escapeHtml(error.message)}</p>`;
    } finally {
        btn.disabled = false;
        btn.textContent = '分析';
    }
}

// 生成投资建议
async function generateRecommendation() {
    const resultArea = document.getElementById('recommendation-result');
    const btn = document.getElementById('recommend-submit');

    const theme = document.getElementById('recommend-theme').value.trim();
    const keywordsRaw = document.getElementById('recommend-keywords').value.trim();
    const riskProfile = document.getElementById('recommend-risk').value;
    const horizonDays = parseInt(document.getElementById('recommend-horizon').value, 10);
    const maxArticles = parseInt(document.getElementById('recommend-max-articles').value, 10);

    if (!theme) {
        resultArea.className = 'recommendation-result error';
        resultArea.innerHTML = '<h3>❌ 请填写主题</h3>';
        return;
    }

    const payload = {
        theme,
        risk_profile: riskProfile,
        horizon_days: Number.isNaN(horizonDays) ? 30 : horizonDays,
        max_articles: Number.isNaN(maxArticles) ? 40 : maxArticles,
    };

    if (keywordsRaw) {
        payload.keywords = keywordsRaw.split(',').map(k => k.trim()).filter(Boolean);
    }

    btn.disabled = true;
    btn.textContent = '生成中...';
    resultArea.className = 'recommendation-result loading';
    resultArea.innerHTML = '<div class="loading">正在生成投资建议</div>';

    try {
        const response = await fetch(`${API_BASE}/analysis/recommendation`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload),
        });

        const result = await response.json();

        if (!result.success) {
            throw new Error(result.error || '生成失败');
        }

        renderRecommendation(result.data, {
            source: 'manual',
            created_at: result.data.generated_at,
        });
    } catch (error) {
        resultArea.className = 'recommendation-result error';
        resultArea.innerHTML = `<h3>❌ 生成失败</h3><p>${escapeHtml(error.message)}</p>`;
    } finally {
        btn.disabled = false;
        btn.textContent = '生成建议';
    }
}

async function loadLatestRecommendation() {
    const resultArea = document.getElementById('recommendation-result');
    if (!resultArea) return;

    const themeInput = document.getElementById('recommend-theme');
    const theme = themeInput ? themeInput.value.trim() : '';
    const query = theme ? `?theme=${encodeURIComponent(theme)}` : '';

    resultArea.className = 'recommendation-result loading';
    resultArea.innerHTML = '<div class="loading">加载最新投资建议...</div>';

    try {
        const response = await fetch(`${API_BASE}/analysis/recommendation/latest${query}`);
        const result = await response.json();

        if (!result.success) {
            throw new Error(result.error || '加载失败');
        }

        if (!result.data) {
            updateRecommendationStatus('暂无自动生成建议，系统正在后台生成中。');
            resultArea.className = 'recommendation-result';
            resultArea.innerHTML = '<div class="loading">暂无建议，请稍后刷新或手动生成。</div>';
            return;
        }

        updateRecommendationStatus(`最新建议生成时间：${formatDate(result.data.created_at)}（自动生成）`);
        renderRecommendation(result.data.payload, {
            source: 'auto',
            created_at: result.data.created_at,
        });
    } catch (error) {
        updateRecommendationStatus('加载最新建议失败，请稍后再试。');
        resultArea.className = 'recommendation-result error';
        resultArea.innerHTML = `<h3>❌ 加载失败</h3><p>${escapeHtml(error.message)}</p>`;
    }
}

function updateRecommendationStatus(message) {
    const statusElement = document.getElementById('recommendation-status');
    if (statusElement) {
        statusElement.textContent = message;
    }
}

function renderRecommendation(data, meta = {}) {
    const resultArea = document.getElementById('recommendation-result');
    if (!data) {
        resultArea.className = 'recommendation-result error';
        resultArea.innerHTML = '<h3>❌ 未返回有效数据</h3>';
        return;
    }

    if (meta.created_at) {
        const prefix = meta.source === 'manual' ? '手动生成时间' : '最新建议生成时间';
        updateRecommendationStatus(`${prefix}：${formatDate(meta.created_at)}`);
    }

    const verification = data.verification || {};
    const synthesis = data.synthesis || {};
    const recommendation = data.recommendation || {};
    const evidence = synthesis.evidence || [];
    const signalProbs = recommendation.signal_probs || {};
    const signalLabel = recommendation.signal || '观望';
    const buyProb = formatProbability(signalProbs.buy);
    const sellProb = formatProbability(signalProbs.sell);
    const holdProb = formatProbability(signalProbs.hold);

    resultArea.className = 'recommendation-result success';
    resultArea.innerHTML = `
        <div class="recommendation-summary">
            <div>
                <h3>建议概览</h3>
                <p>${escapeHtml(recommendation.outlook || '暂无结论')}</p>
                <div class="signal-summary">
                    <span class="signal-label">明确建议：</span>
                    <span class="signal-value signal-${getSignalClass(signalLabel)}">${escapeHtml(signalLabel)}</span>
                    <div class="signal-probabilities">
                        <span>买入 ${buyProb}</span>
                        <span>卖出 ${sellProb}</span>
                        <span>观望 ${holdProb}</span>
                    </div>
                </div>
            </div>
            <div class="confidence-badge confidence-${getConfidenceClass(recommendation.confidence)}">
                置信度 ${(recommendation.confidence || 0).toFixed(2)}
            </div>
        </div>

        <div class="recommendation-grid">
            <div class="recommendation-card">
                <h4>验证摘要</h4>
                <p>${escapeHtml(verification.summary || '暂无')}</p>
                <div class="recommendation-meta">
                    <span>来源覆盖：${verification.source_diversity || 0}</span>
                    <span>近48小时占比：${((verification.recent_ratio || 0) * 100).toFixed(0)}%</span>
                    <span>平均置信度：${(verification.avg_confidence || 0).toFixed(2)}</span>
                </div>
            </div>
            <div class="recommendation-card">
                <h4>核心驱动因素</h4>
                <ul>
                    ${(synthesis.drivers || []).map(item => `<li>${escapeHtml(item)}</li>`).join('') || '<li>暂无</li>'}
                </ul>
            </div>
            <div class="recommendation-card">
                <h4>风险提示</h4>
                <ul>
                    ${(synthesis.risks || []).map(item => `<li>${escapeHtml(item)}</li>`).join('') || '<li>暂无</li>'}
                </ul>
            </div>
            <div class="recommendation-card">
                <h4>潜在催化剂</h4>
                <ul>
                    ${(synthesis.catalysts || []).map(item => `<li>${escapeHtml(item)}</li>`).join('') || '<li>暂无</li>'}
                </ul>
            </div>
        </div>

        <div class="recommendation-card">
            <h4>可执行建议</h4>
            <ul>
                ${(recommendation.actions || []).map(item => `<li>${escapeHtml(item)}</li>`).join('') || '<li>暂无</li>'}
            </ul>
            <div class="recommendation-note">
                ${(recommendation.risk_notes || []).map(item => `<p>⚠️ ${escapeHtml(item)}</p>`).join('') || '<p>暂无风险提示</p>'}
            </div>
        </div>

        <div class="recommendation-card">
            <h4>关注清单</h4>
            <ul>
                ${(recommendation.watchlist || []).map(item => `<li>${escapeHtml(item)}</li>`).join('') || '<li>暂无</li>'}
            </ul>
        </div>

        <div class="recommendation-card">
            <h4>关键证据</h4>
            ${evidence.length ? `
                <ul class="evidence-list">
                    ${evidence.map(item => `
                        <li>
                            <a href="${escapeHtml(item.url || '#')}" target="_blank" rel="noopener noreferrer">
                                ${escapeHtml(item.title || '未知标题')}
                            </a>
                            <span>${escapeHtml(item.source || '未知')} · ${formatDate(item.published_at)}</span>
                        </li>
                    `).join('')}
                </ul>
            ` : '<p>暂无证据</p>'}
        </div>
    `;
}

function getConfidenceClass(confidence) {
    if (confidence >= 0.75) return 'high';
    if (confidence >= 0.5) return 'medium';
    return 'low';
}

function getSignalClass(signal) {
    if (signal === '买入') return 'buy';
    if (signal === '卖出') return 'sell';
    return 'hold';
}

function formatProbability(value) {
    if (typeof value !== 'number' || Number.isNaN(value)) {
        return '—';
    }
    return `${(value * 100).toFixed(0)}%`;
}

// 加载统计数据
async function loadStats() {
    const statsContent = document.getElementById('stats-content');
    statsContent.innerHTML = '<div class="loading">加载中</div>';
    
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const result = await response.json();
        
        if (result.success) {
            const stats = result.stats;
            statsContent.innerHTML = `
                <div class="stat-card">
                    <h3>总文章数</h3>
                    <div class="stat-value">${stats.total_articles || 0}</div>
                </div>
                <div class="stat-card">
                    <h3>高置信度文章</h3>
                    <div class="stat-value">${stats.high_confidence_articles || 0}</div>
                </div>
                <div class="stat-card">
                    <h3>平均置信度</h3>
                    <div class="stat-value">${(stats.average_confidence || 0).toFixed(2)}</div>
                </div>
            `;
        } else {
            throw new Error(result.error || '加载失败');
        }
    } catch (error) {
        statsContent.innerHTML = `<div class="result-area error" style="display: block;">
            <h3>❌ 加载失败</h3><p>${escapeHtml(error.message)}</p>
        </div>`;
    }
}

// 辅助函数
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    if (!dateString) return '未知';
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' });
}

function getImpactClass(impact) {
    if (!impact) return 'unknown';
    const impactLower = impact.toLowerCase();
    if (impactLower.includes('上涨') || impactLower.includes('up') || impactLower.includes('rise')) {
        return 'up';
    } else if (impactLower.includes('下跌') || impactLower.includes('down') || impactLower.includes('fall')) {
        return 'down';
    } else if (impactLower.includes('中性') || impactLower.includes('neutral')) {
        return 'neutral';
    }
    return 'unknown';
}

// 加载文章列表
let articlesRefreshInterval = null;

async function loadArticles() {
    const articlesList = document.getElementById('articles-list');
    articlesList.innerHTML = '<div class="loading">加载中</div>';
    
    const limit = parseInt(document.getElementById('articles-limit').value) || 20;
    const minScore = parseFloat(document.getElementById('articles-min-score').value) || 0.7;
    
    const params = new URLSearchParams();
    params.append('high_confidence', 'true');
    params.append('min_score', minScore);
    params.append('limit', limit);
    
    try {
        const response = await fetch(`${API_BASE}/articles?${params.toString()}`);
        const result = await response.json();
        
        if (result.success) {
            if (result.articles.length === 0) {
                articlesList.innerHTML = '<div class="result-area" style="display: block; background: #fff3cd; border: 1px solid #ffeaa7; color: #856404;">暂无高置信度文章，系统正在持续搜索中...</div>';
                return;
            }
            
            articlesList.innerHTML = result.articles.map(article => `
                <div class="article-item">
                    <div class="article-header">
                        <div class="article-title">
                            <a href="${escapeHtml(article.url)}" target="_blank" rel="noopener noreferrer">
                                ${escapeHtml(article.title)}
                            </a>
                        </div>
                        <div class="article-score">${article.confidence_score.toFixed(2)}</div>
                    </div>
                    <div class="article-meta">
                        <span><strong>来源：</strong>${escapeHtml(article.source || '未知')}</span>
                        <span><strong>发布时间：</strong>${formatDate(article.published_at)}</span>
                        <span><strong>相关性：</strong>${article.relevance_score.toFixed(2)}</span>
                        <span><strong>可靠性：</strong>${article.reliability_score.toFixed(2)}</span>
                        ${article.keywords ? `<span><strong>关键词：</strong>${escapeHtml(article.keywords)}</span>` : ''}
                    </div>
                    ${article.content ? `
                        <div class="article-content">
                            ${escapeHtml(article.content.substring(0, 500))}${article.content.length > 500 ? '...' : ''}
                        </div>
                    ` : ''}
                    ${article.ai_analysis ? `
                        <div class="article-analysis">
                            <strong>AI分析：</strong><br>
                            ${escapeHtml(article.ai_analysis)}
                        </div>
                    ` : ''}
                </div>
            `).join('');
        } else {
            throw new Error(result.error || '加载失败');
        }
    } catch (error) {
        articlesList.innerHTML = `<div class="result-area error" style="display: block;">
            <h3>❌ 加载失败</h3><p>${escapeHtml(error.message)}</p>
        </div>`;
    }
}

// 工作流程图相关函数
let workflowRefreshInterval = null;

async function refreshWorkflow() {
    try {
        // 并行获取统计数据、关键词数据、配置信息
        const [statsResponse, keywordsResponse, configResponse, schedulerResponse] = await Promise.all([
            fetch(`${API_BASE}/stats`),
            fetch(`${API_BASE}/keywords?limit=1000`),
            fetch(`${API_BASE}/config`),
            fetch(`${API_BASE}/scheduler/status`)
        ]);
        
        const statsResult = await statsResponse.json();
        const keywordsResult = await keywordsResponse.json();
        const configResult = await configResponse.json();
        const schedulerResult = await schedulerResponse.json();
        
        if (statsResult.success) {
            const stats = statsResult.stats;
            
            // 更新步骤4（信息评估）的数据
            document.getElementById('total-articles').textContent = stats.total_articles || 0;
            document.getElementById('high-confidence-articles').textContent = stats.high_confidence_articles || 0;
            document.getElementById('avg-confidence').textContent = (stats.average_confidence || 0).toFixed(2);
            
            // 根据数据更新步骤状态
            updateStepStatus(4, stats.total_articles > 0 ? 'completed' : 'pending');
            if (stats.high_confidence_articles > 0) {
                updateStepStatus(5, 'active');
                updateStepStatus(6, 'active');
            }
        }
        
        if (keywordsResult.success) {
            const keywords = keywordsResult.keywords || [];
            const activeKeywords = keywords.filter(kw => kw.is_active);
            
            // 更新步骤2（关键词挖掘）的数据
            document.getElementById('keyword-count').textContent = keywords.length;
            document.getElementById('active-keyword-count').textContent = activeKeywords.length;
            
            // 根据关键词数量更新步骤状态
            if (keywords.length > 0) {
                updateStepStatus(2, 'completed');
                updateStepStatus(3, 'active');
            } else {
                updateStepStatus(2, 'processing');
            }
        }
        
        if (configResult.success) {
            const config = configResult.config;
            const searchInterval = document.getElementById('search-interval');
            const searchCount = document.getElementById('search-count');
            if (searchInterval) searchInterval.textContent = `${config.search_interval_minutes}分钟`;
            if (searchCount) searchCount.textContent = config.max_articles_per_search;
        }

        if (schedulerResult.success && schedulerResult.scheduler) {
            renderSchedulerStatus(schedulerResult.scheduler);
        } else {
            renderSchedulerStatusError(schedulerResult.error || '无法获取调度器状态');
        }
        
        // 步骤1（主题设定）始终是完成的
        updateStepStatus(1, 'completed');
        
        // 加载涨跌概率分析数据
        try {
            const trendResponse = await fetch(`${API_BASE}/analysis/price-trend?limit=20&hours=168`);
            const trendResult = await trendResponse.json();
            
            if (trendResult.success && trendResult.analysis) {
                const analysis = trendResult.analysis;
                const upProb = document.getElementById('up-probability');
                const downProb = document.getElementById('down-probability');
                const neutralProb = document.getElementById('neutral-probability');
                if (upProb) upProb.textContent = `${analysis.up_probability}%`;
                if (downProb) downProb.textContent = `${analysis.down_probability}%`;
                if (neutralProb) neutralProb.textContent = `${analysis.neutral_probability}%`;
            }
        } catch (error) {
            console.error('加载涨跌分析失败:', error);
        }
        
        // 如果步骤详情已展开，刷新详细数据
        for (let i = 1; i <= 6; i++) {
            const detailContent = document.getElementById(`step-${i}-details`);
            if (detailContent && detailContent.style.display !== 'none') {
                loadStepDetails(i);
            }
        }
        
    } catch (error) {
        console.error('刷新工作流程状态失败:', error);
    }
}

function renderSchedulerStatusError(message) {
    const list = document.getElementById('scheduler-status-list');
    const updatedAt = document.getElementById('scheduler-updated-at');
    if (updatedAt) {
        updatedAt.textContent = formatDate(new Date().toISOString());
    }
    if (list) {
        list.innerHTML = `<div class="result-area error" style="display: block;">
            <h3>❌ 状态加载失败</h3><p>${escapeHtml(message)}</p>
        </div>`;
    }
}

function renderSchedulerStatus(scheduler) {
    const list = document.getElementById('scheduler-status-list');
    const updatedAt = document.getElementById('scheduler-updated-at');
    if (!list) return;

    if (updatedAt) {
        updatedAt.textContent = scheduler.server_time ? formatDate(scheduler.server_time) : '未知';
    }

    const tasks = scheduler.tasks || [];
    if (!tasks.length) {
        list.innerHTML = '<div class="result-area" style="display: block; background: #fff3cd; border: 1px solid #ffeaa7; color: #856404;">暂无任务状态</div>';
        return;
    }

    list.innerHTML = tasks.map(task => {
        const statusLabel = task.is_running ? '运行中' : task.last_status === 'error' ? '异常' : scheduler.running ? '待机中' : '未运行';
        const statusClass = task.is_running ? 'running' : task.last_status === 'error' ? 'error' : scheduler.running ? 'idle' : 'offline';
        const duration = formatDuration(task.last_duration_seconds);
        const lastRun = task.last_run ? formatDate(task.last_run) : '尚未执行';
        const nextRun = task.next_run ? formatDate(task.next_run) : '未安排';

        return `
            <div class="scheduler-status-item">
                <div class="scheduler-task-header">
                    <div>
                        <h3>${escapeHtml(task.label)}</h3>
                        <p class="scheduler-interval">${escapeHtml(task.interval)}</p>
                    </div>
                    <span class="scheduler-status-badge scheduler-status-${statusClass}">${statusLabel}</span>
                </div>
                <div class="scheduler-task-meta">
                    <div><strong>上次执行：</strong>${lastRun}</div>
                    <div><strong>耗时：</strong>${duration}</div>
                    <div><strong>下次执行：</strong>${nextRun}</div>
                </div>
                ${task.last_error ? `<div class="scheduler-task-error">⚠️ ${escapeHtml(task.last_error)}</div>` : ''}
            </div>
        `;
    }).join('');
}

function formatDuration(seconds) {
    if (typeof seconds !== 'number' || Number.isNaN(seconds)) {
        return '—';
    }
    if (seconds < 1) {
        return `${(seconds * 1000).toFixed(0)} ms`;
    }
    if (seconds < 60) {
        return `${seconds.toFixed(1)} 秒`;
    }
    const minutes = Math.floor(seconds / 60);
    const remaining = Math.round(seconds % 60);
    return `${minutes} 分 ${remaining} 秒`;
}

function updateStepStatus(stepNumber, status) {
    const stepElement = document.getElementById(`step-${stepNumber}`);
    const statusIndicator = document.getElementById(`status-${stepNumber}`);
    
    if (!stepElement || !statusIndicator) return;
    
    // 移除所有状态类
    stepElement.classList.remove('active', 'processing', 'completed');
    statusIndicator.classList.remove('active', 'processing', 'completed');
    
    // 添加新状态类
    if (status === 'active') {
        stepElement.classList.add('active');
        statusIndicator.classList.add('active');
    } else if (status === 'processing') {
        stepElement.classList.add('processing');
        statusIndicator.classList.add('processing');
    } else if (status === 'completed') {
        stepElement.classList.add('completed');
        statusIndicator.classList.add('completed');
    }
}

// 切换步骤详情显示
function toggleStepDetails(stepNumber) {
    const detailContent = document.getElementById(`step-${stepNumber}-details`);
    const toggleButton = document.querySelector(`[data-step="${stepNumber}"].btn-toggle-details`);
    
    if (!detailContent || !toggleButton) return;
    
    const isVisible = detailContent.style.display !== 'none';
    
    if (isVisible) {
        detailContent.style.display = 'none';
        toggleButton.classList.remove('expanded');
        toggleButton.querySelector('.toggle-text').textContent = '查看详情';
    } else {
        detailContent.style.display = 'block';
        toggleButton.classList.add('expanded');
        toggleButton.querySelector('.toggle-text').textContent = '隐藏详情';
        
        // 加载详细数据
        loadStepDetails(stepNumber);
    }
}

// 加载步骤详细数据
async function loadStepDetails(stepNumber) {
    try {
        if (stepNumber === 2) {
            // 加载关键词列表
            const response = await fetch(`${API_BASE}/keywords?limit=20&active=true`);
            const result = await response.json();
            
            if (result.success && result.keywords) {
                const keywordsList = document.getElementById('keywords-list-detail');
                if (keywordsList) {
                    if (result.keywords.length === 0) {
                        keywordsList.innerHTML = '<div style="color: #666; text-align: center; padding: 20px;">暂无关键词</div>';
                    } else {
                        keywordsList.innerHTML = result.keywords.slice(0, 10).map(kw => `
                            <div class="keyword-detail-item">
                                <span class="keyword-name">${escapeHtml(kw.keyword)}</span>
                                <div class="keyword-meta-info">
                                    <span>相关性: ${kw.relevance_score.toFixed(2)}</span>
                                    <span>影响: ${kw.impact || '未知'}</span>
                                </div>
                            </div>
                        `).join('') + (result.keywords.length > 10 ? `<div style="text-align: center; color: #666; padding: 10px;">还有 ${result.keywords.length - 10} 个关键词...</div>` : '');
                    }
                }
            }
        } else if (stepNumber === 3) {
            // 加载检索配置
            const response = await fetch(`${API_BASE}/config`);
            const result = await response.json();
            
            if (result.success && result.config) {
                const minConfidence = document.getElementById('min-confidence-threshold');
                if (minConfidence) {
                    minConfidence.textContent = result.config.min_confidence_score.toFixed(2);
                }
            }
        } else if (stepNumber === 4) {
            // 加载评估统计
            const response = await fetch(`${API_BASE}/stats`);
            const result = await response.json();
            
            if (result.success && result.stats) {
                const stats = result.stats;
                const avgConfidence = document.getElementById('detail-avg-confidence');
                const highConfidenceRatio = document.getElementById('high-confidence-ratio');
                
                if (avgConfidence) {
                    avgConfidence.textContent = (stats.average_confidence || 0).toFixed(2);
                }
                
                if (highConfidenceRatio && stats.total_articles > 0) {
                    const ratio = ((stats.high_confidence_articles || 0) / stats.total_articles * 100).toFixed(1);
                    highConfidenceRatio.textContent = `${ratio}%`;
                } else if (highConfidenceRatio) {
                    highConfidenceRatio.textContent = '0%';
                }
            }
        } else if (stepNumber === 5) {
            // 加载涨跌概率分析
            const response = await fetch(`${API_BASE}/analysis/price-trend?limit=20&hours=168`);
            const result = await response.json();
            
            if (result.success && result.analysis) {
                const analysisContainer = document.getElementById('price-trend-analysis');
                if (analysisContainer) {
                    const analysis = result.analysis;
                    
                    // 更新概览数据
                    const upProb = document.getElementById('up-probability');
                    const downProb = document.getElementById('down-probability');
                    const neutralProb = document.getElementById('neutral-probability');
                    if (upProb) upProb.textContent = `${analysis.up_probability}%`;
                    if (downProb) downProb.textContent = `${analysis.down_probability}%`;
                    if (neutralProb) neutralProb.textContent = `${analysis.neutral_probability}%`;
                    
                    // 显示详细分析
                    let factorsHtml = '';
                    if (analysis.factors && analysis.factors.length > 0) {
                        factorsHtml = `
                            <div class="trend-factors">
                                <h5>关键因素：</h5>
                                <ul>
                                    ${analysis.factors.map(factor => `<li>${escapeHtml(factor)}</li>`).join('')}
                                </ul>
                            </div>
                        `;
                    }
                    
                    const confidenceClass = analysis.confidence === 'high' ? 'high' : analysis.confidence === 'low' ? 'low' : 'medium';
                    
                    analysisContainer.innerHTML = `
                        <div class="trend-probability-bars">
                            <div class="probability-bar up">
                                <div class="bar-label">上涨 ${analysis.up_probability}%</div>
                                <div class="bar-fill" style="width: ${analysis.up_probability}%; background: #28a745;"></div>
                            </div>
                            <div class="probability-bar down">
                                <div class="bar-label">下跌 ${analysis.down_probability}%</div>
                                <div class="bar-fill" style="width: ${analysis.down_probability}%; background: #dc3545;"></div>
                            </div>
                            <div class="probability-bar neutral">
                                <div class="bar-label">中性 ${analysis.neutral_probability}%</div>
                                <div class="bar-fill" style="width: ${analysis.neutral_probability}%; background: #6c757d;"></div>
                            </div>
                        </div>
                        <div class="trend-summary">
                            <h5>简要分析：</h5>
                            <p>${escapeHtml(analysis.summary || '暂无分析')}</p>
                        </div>
                        ${factorsHtml}
                        <div class="trend-confidence">
                            <span class="confidence-label">分析置信度：</span>
                            <span class="confidence-badge confidence-${confidenceClass}">${analysis.confidence === 'high' ? '高' : analysis.confidence === 'low' ? '低' : '中'}</span>
                        </div>
                    `;
                }
            }
        } else if (stepNumber === 6) {
            // 加载高置信度文章列表
            const response = await fetch(`${API_BASE}/articles?high_confidence=true&limit=10&min_score=0.7`);
            const result = await response.json();
            
            if (result.success && result.articles) {
                const articlesList = document.getElementById('articles-list-detail');
                if (articlesList) {
                    if (result.articles.length === 0) {
                        articlesList.innerHTML = '<div style="color: #666; text-align: center; padding: 20px;">暂无高置信度文章</div>';
                    } else {
                        articlesList.innerHTML = result.articles.map(article => `
                            <div class="article-detail-item">
                                <div class="article-title">
                                    <a href="${escapeHtml(article.url)}" target="_blank" rel="noopener noreferrer">
                                        ${escapeHtml(article.title)}
                                    </a>
                                </div>
                                <div class="article-meta-info">
                                    <span>置信度: ${article.confidence_score.toFixed(2)}</span>
                                    <span>来源: ${escapeHtml(article.source || '未知')}</span>
                                    <span>发布时间: ${formatDate(article.published_at)}</span>
                                </div>
                            </div>
                        `).join('');
                    }
                }
            }
        }
    } catch (error) {
        console.error(`加载步骤${stepNumber}详细数据失败:`, error);
    }
}

// 设置工作流程图自动刷新
function setupWorkflowAutoRefresh() {
    const autoRefreshCheckbox = document.getElementById('workflow-auto-refresh');
    
    // 清除现有定时器
    if (workflowRefreshInterval) {
        clearInterval(workflowRefreshInterval);
        workflowRefreshInterval = null;
    }
    
    // 如果启用自动刷新，设置定时器
    if (autoRefreshCheckbox && autoRefreshCheckbox.checked) {
        workflowRefreshInterval = setInterval(() => {
            // 只在"工作流程"标签页激活时刷新
            const workflowTab = document.getElementById('workflow-tab');
            if (workflowTab && workflowTab.classList.contains('active')) {
                refreshWorkflow();
            }
        }, 10000); // 10秒刷新一次
    }
}

// 设置自动刷新
function setupAutoRefresh() {
    const autoRefreshCheckbox = document.getElementById('auto-refresh');
    
    // 清除现有定时器
    if (articlesRefreshInterval) {
        clearInterval(articlesRefreshInterval);
        articlesRefreshInterval = null;
    }
    
    // 如果启用自动刷新，设置定时器
    if (autoRefreshCheckbox && autoRefreshCheckbox.checked) {
        articlesRefreshInterval = setInterval(() => {
            // 只在"实时发现"标签页激活时刷新
            const articlesTab = document.getElementById('articles-tab');
            if (articlesTab && articlesTab.classList.contains('active')) {
                loadArticles();
            }
        }, 30000); // 30秒刷新一次
    }
}

// 加载股票列表
async function loadStocks() {
    const stocksList = document.getElementById('stocks-list');
    stocksList.innerHTML = '<div class="loading">加载中</div>';
    
    const active = document.getElementById('stocks-active').value;
    const limit = parseInt(document.getElementById('stocks-limit').value) || 50;
    const stockTypeSelect = document.getElementById('stocks-type');
    const stockType = stockTypeSelect ? stockTypeSelect.value : '';
    
    const params = new URLSearchParams();
    if (active) params.append('active', active);
    if (limit) params.append('limit', limit);
    if (stockType) params.append('stock_type', stockType);
    
    try {
        const response = await fetch(`${API_BASE}/stocks/identified?${params.toString()}`);
        const result = await response.json();
        
        if (result.success) {
            if (result.stocks.length === 0) {
                stocksList.innerHTML = '<div class="result-area" style="display: block; background: #fff3cd; border: 1px solid #ffeaa7; color: #856404;">暂无识别的股票，点击"识别股票"按钮开始识别</div>';
                return;
            }
            
            // 为每个股票获取最新价格
            const stocksWithPrices = await Promise.all(
                result.stocks.map(async (stock) => {
                    try {
                        const priceUrl = `${API_BASE}/stocks/${stock.symbol}/price${stock.stock_type ? `?type=${stock.stock_type}` : ''}`;
                        const priceResponse = await fetch(priceUrl);
                        // 确保响应是成功的（200状态码）
                        if (!priceResponse.ok) {
                            console.warn(`获取股票 ${stock.symbol} 价格失败: HTTP ${priceResponse.status}`);
                            return { ...stock, current_price: null };
                        }
                        const priceResult = await priceResponse.json();
                        return {
                            ...stock,
                            current_price: priceResult.success ? priceResult.price : null,
                            price_error: priceResult.success ? null : (priceResult.error || '无法获取价格')
                        };
                    } catch (e) {
                        console.error(`获取股票 ${stock.symbol} 价格出错:`, e);
                        return { ...stock, current_price: null, price_error: '网络错误' };
                    }
                })
            );
            
            stocksList.innerHTML = stocksWithPrices.map(stock => `
                <div class="stock-item">
                    <div class="stock-header">
                        <div class="stock-symbol-info">
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <span class="stock-symbol">${escapeHtml(stock.symbol)}</span>
                                ${stock.stock_type ? `
                                    <span class="stock-type-badge stock-type-${stock.stock_type}">
                                        ${stock.stock_type === 'us_stock' ? '美股' : stock.stock_type === 'a_stock' ? 'A股' : '期货'}
                                    </span>
                                ` : ''}
                                ${stock.market ? `<span style="font-size: 0.85em; color: #666;">${escapeHtml(stock.market)}</span>` : ''}
                            </div>
                            ${stock.company_name ? `<span class="stock-company">${escapeHtml(stock.company_name)}</span>` : ''}
                        </div>
                        ${stock.current_price ? `
                            <div class="stock-price-info">
                                <span class="stock-price">
                                    ${stock.stock_type === 'a_stock' || stock.stock_type === 'futures' ? '' : '$'}${stock.current_price.price?.toFixed(2) || 'N/A'}
                                    ${stock.stock_type === 'a_stock' ? '元' : stock.stock_type === 'futures' ? '元/手' : ''}
                                </span>
                                ${stock.current_price.change !== null ? `
                                    <span class="stock-change ${stock.current_price.change >= 0 ? 'positive' : 'negative'}">
                                        ${stock.current_price.change >= 0 ? '+' : ''}${stock.current_price.change?.toFixed(2) || '0.00'} 
                                        (${stock.current_price.change_percent >= 0 ? '+' : ''}${stock.current_price.change_percent?.toFixed(2) || '0.00'}%)
                                    </span>
                                ` : ''}
                                ${stock.current_price.source === 'database' ? '<span style="font-size: 0.8em; color: #666; margin-left: 5px;">(历史数据)</span>' : ''}
                            </div>
                        ` : `
                            <div class="stock-price-info">
                                <span class="stock-price" style="color: #999;">
                                    ${stock.price_error ? `⚠️ ${escapeHtml(stock.price_error)}` : '价格加载中...'}
                                </span>
                            </div>
                        `}
                    </div>
                    <div class="stock-meta">
                        ${stock.relevance ? `<span><strong>相关性：</strong>${escapeHtml(stock.relevance)}</span>` : ''}
                        <span><strong>识别时间：</strong>${formatDate(stock.identified_at)}</span>
                        <span><strong>状态：</strong>${stock.is_active ? '✅ 活跃' : '❌ 非活跃'}</span>
                    </div>
                    <div class="stock-actions">
                        <button class="btn btn-small" onclick="showStockChart('${escapeHtml(stock.symbol)}')">查看走势</button>
                        <button class="btn btn-small" onclick="updateStockPrice('${escapeHtml(stock.symbol)}')">更新价格</button>
                    </div>
                </div>
            `).join('');
        } else {
            throw new Error(result.error || '加载失败');
        }
    } catch (error) {
        stocksList.innerHTML = `<div class="result-area error" style="display: block;">
            <h3>❌ 加载失败</h3><p>${escapeHtml(error.message)}</p>
        </div>`;
    }
}

// 识别股票
async function identifyStocks() {
    const btn = event.target;
    btn.disabled = true;
    btn.textContent = '识别中...';
    
    try {
        const response = await fetch(`${API_BASE}/stocks/identify`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                source: 'keywords'  // 或 'articles'
            }),
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert(`识别成功！共识别 ${result.identified} 只股票，保存了 ${result.saved} 只`);
            loadStocks();
        } else {
            throw new Error(result.error || '识别失败');
        }
    } catch (error) {
        alert(`识别失败: ${escapeHtml(error.message)}`);
    } finally {
        btn.disabled = false;
        btn.textContent = '识别股票';
    }
}

// 更新股票价格
async function updateStockPrices() {
    const btn = event.target;
    btn.disabled = true;
    btn.textContent = '更新中...';
    
    try {
        const response = await fetch(`${API_BASE}/stocks/update`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({}),
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert(`更新成功！更新了 ${result.updated} / ${result.total} 只股票的价格`);
            loadStocks();
        } else {
            throw new Error(result.error || '更新失败');
        }
    } catch (error) {
        alert(`更新失败: ${escapeHtml(error.message)}`);
    } finally {
        btn.disabled = false;
        btn.textContent = '更新价格';
    }
}

// 更新单个股票价格
async function updateStockPrice(symbol) {
    try {
        const response = await fetch(`${API_BASE}/stocks/update`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                symbols: symbol
            }),
        });
        
        const result = await response.json();
        
        if (result.success) {
            loadStocks();
        } else {
            throw new Error(result.error || '更新失败');
        }
    } catch (error) {
        alert(`更新失败: ${escapeHtml(error.message)}`);
    }
}

// 显示股票走势图
async function showStockChart(symbol) {
    // 创建模态窗口显示走势图
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content" style="max-width: 900px;">
            <div class="modal-header">
                <h3>${symbol} 走势图</h3>
                <button class="modal-close" onclick="this.closest('.modal').remove()">×</button>
            </div>
            <div class="modal-body">
                <div id="chart-container" style="width: 100%; height: 400px;">
                    <div class="loading">加载走势数据中...</div>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    
    try {
        // 获取走势数据
        const response = await fetch(`${API_BASE}/stocks/${symbol}/chart?type=daily&days=30`);
        const result = await response.json();
        
        if (result.success && result.data) {
            // 使用简单的Canvas绘制走势图
            drawStockChart(result.data, symbol);
        } else {
            document.getElementById('chart-container').innerHTML = 
                `<div class="result-area error" style="display: block;">无法加载走势数据</div>`;
        }
    } catch (error) {
        document.getElementById('chart-container').innerHTML = 
            `<div class="result-area error" style="display: block;">加载失败: ${escapeHtml(error.message)}</div>`;
    }
}

// 绘制股票走势图
function drawStockChart(data, symbol) {
    const container = document.getElementById('chart-container');
    container.innerHTML = `<canvas id="stock-chart-canvas" width="850" height="400"></canvas>`;
    
    const canvas = document.getElementById('stock-chart-canvas');
    const ctx = canvas.getContext('2d');
    
    if (!data || data.length === 0) {
        ctx.fillStyle = '#666';
        ctx.font = '16px Arial';
        ctx.fillText('暂无数据', 400, 200);
        return;
    }
    
    const width = canvas.width;
    const height = canvas.height;
    const padding = 40;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;
    
    // 计算价格范围
    const prices = data.map(d => d.close).filter(p => p !== null);
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);
    const priceRange = maxPrice - minPrice || 1;
    
    // 绘制背景
    ctx.fillStyle = '#f5f5f5';
    ctx.fillRect(0, 0, width, height);
    
    // 绘制网格线
    ctx.strokeStyle = '#ddd';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 5; i++) {
        const y = padding + (chartHeight / 5) * i;
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(width - padding, y);
        ctx.stroke();
    }
    
    // 绘制价格线
    ctx.strokeStyle = '#667eea';
    ctx.lineWidth = 2;
    ctx.beginPath();
    
    data.forEach((point, index) => {
        const x = padding + (chartWidth / (data.length - 1)) * index;
        const y = padding + chartHeight - ((point.close - minPrice) / priceRange) * chartHeight;
        
        if (index === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    });
    ctx.stroke();
    
    // 绘制数据点
    ctx.fillStyle = '#667eea';
    data.forEach((point, index) => {
        const x = padding + (chartWidth / (data.length - 1)) * index;
        const y = padding + chartHeight - ((point.close - minPrice) / priceRange) * chartHeight;
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, 2 * Math.PI);
        ctx.fill();
    });
    
    // 绘制标签
    ctx.fillStyle = '#333';
    ctx.font = '12px Arial';
    
    // Y轴标签（价格）
    for (let i = 0; i <= 5; i++) {
        const price = maxPrice - (priceRange / 5) * i;
        const y = padding + (chartHeight / 5) * i;
        ctx.fillText(`$${price.toFixed(2)}`, 5, y + 4);
    }
    
    // X轴标签（日期）
    const labelCount = Math.min(5, data.length);
    for (let i = 0; i < labelCount; i++) {
        const index = Math.floor((data.length - 1) / (labelCount - 1)) * i;
        if (index < data.length) {
            const x = padding + (chartWidth / (data.length - 1)) * index;
            const date = new Date(data[index].timestamp);
            const dateStr = `${date.getMonth() + 1}/${date.getDate()}`;
            ctx.fillText(dateStr, x - 15, height - 10);
        }
    }
    
    // 标题
    ctx.font = 'bold 16px Arial';
    ctx.fillText(`${symbol} 价格走势 (30天)`, padding, 25);
}

// 加载AI配置信息
async function loadAIConfig() {
    try {
        const response = await fetch(`${API_BASE}/config`);
        const result = await response.json();
        
        if (result.success && result.ai_config) {
            const aiConfig = result.ai_config;
            const apiSourceElement = document.getElementById('ai-api-source');
            const modelElement = document.getElementById('ai-model');
            
            if (apiSourceElement) {
                if (aiConfig.configured) {
                    apiSourceElement.textContent = aiConfig.api_source;
                } else {
                    apiSourceElement.textContent = '未配置';
                    apiSourceElement.style.color = '#ffc107';
                }
            }
            
            if (modelElement) {
                if (aiConfig.configured) {
                    modelElement.textContent = aiConfig.model;
                } else {
                    modelElement.textContent = '无';
                    modelElement.style.color = '#ffc107';
                }
            }
        }
    } catch (error) {
        console.error('加载AI配置信息失败:', error);
        const apiSourceElement = document.getElementById('ai-api-source');
        const modelElement = document.getElementById('ai-model');
        if (apiSourceElement) apiSourceElement.textContent = '加载失败';
        if (modelElement) modelElement.textContent = '加载失败';
    }
}

// 监听自动刷新复选框变化
document.addEventListener('DOMContentLoaded', () => {
    const autoRefreshCheckbox = document.getElementById('auto-refresh');
    if (autoRefreshCheckbox) {
        autoRefreshCheckbox.addEventListener('change', setupAutoRefresh);
    }
    
    const workflowAutoRefreshCheckbox = document.getElementById('workflow-auto-refresh');
    if (workflowAutoRefreshCheckbox) {
        workflowAutoRefreshCheckbox.addEventListener('change', setupWorkflowAutoRefresh);
    }
    
    // 监听文章筛选条件变化
    const articlesLimit = document.getElementById('articles-limit');
    const articlesMinScore = document.getElementById('articles-min-score');
    if (articlesLimit) {
        articlesLimit.addEventListener('change', loadArticles);
    }
    if (articlesMinScore) {
        articlesMinScore.addEventListener('change', loadArticles);
    }
    
    // 初始化自动刷新
    setupAutoRefresh();
    setupWorkflowAutoRefresh();
    
    // 页面加载时加载工作流程图和统计数据
    refreshWorkflow();
    loadStats();
    loadAIConfig();
    loadLatestRecommendation();
});
