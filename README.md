# QuantMAx - 分钟级多头超短量化系统

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **在 A 股主线题材与热榜股票中，用模型筛选最强分钟级 Alpha 信号，规避涨停与流动性陷阱，按固定节奏做 TopK 多头超短交易，并通过严格风控确保资金安全。**

---

## 📦 1. 本地部署

### 环境要求
- macOS / Linux
- Python 3.11+

### 一键部署

```bash
# 1. 克隆仓库
git clone https://github.com/Bronc-X/QuantMax.git
cd QuantMax

# 2. 创建虚拟环境
python3.11 -m venv .venv
source .venv/bin/activate

# 3. 安装依赖
pip install -e .

# 4. 下载分钟线数据
quantopen download-1m

# 5. 运行回测验证
quantopen backtest
```

---

## 🎯 2. 核心功能

| 功能 | 命令 | 说明 |
|------|------|------|
| **数据下载** | `quantopen download-1m` | AkShare 东方财富分钟线 |
| **基础回测** | `quantopen backtest` | HoldNMinutes 策略 |
| **风控回测** | `quantopen backtest-risk` | 涨停/流动性/回撤过滤 |
| **核心策略** | `quantopen backtest-core` | 可插拔策略接口 |
| **Qlib导出** | `quantopen export-qlib` | 导出 Qlib 格式数据 |

### 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    QuantMAx 系统架构                         │
├─────────────────────────────────────────────────────────────┤
│  数据层: AkShare → Parquet 缓存 → Backtrader Feed            │
├─────────────────────────────────────────────────────────────┤
│  策略层: CoreStrategy (可插拔策略接口)                        │
│    ├── alpha_score()        # 模型打分                      │
│    ├── filter_and_select()  # 过滤裁决                      │
│    └── build_target_weights() # 组合执行                    │
├─────────────────────────────────────────────────────────────┤
│  回测层: Backtrader + A股佣金模型 + 分析器                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧠 3. 核心策略逻辑

### 三层决策系统

#### 1️⃣ Alpha 打分层

```
FinalScore = BaseScore × HotRankWeight × ThemeBoost
```

| 因子 | 作用 |
|------|------|
| BaseScore | 动量/模型分数，捕捉短期强势 |
| HotRankWeight | 热榜排名加权 |
| ThemeBoost | 主题趋势增强 |

#### 2️⃣ 过滤与裁决层

| 过滤规则 | 条件 | 目的 |
|----------|------|------|
| 热榜过滤 | rank ≤ 50 | 保证市场注意力 |
| 涨停过滤 | 涨幅 < 9.5% | 避免流动性陷阱 |
| 流动性过滤 | 成交额 ≥ 200万 | 控制滑点 |

#### 3️⃣ 组合与执行层

| 规则 | 参数 |
|------|------|
| TopK选择 | topk=5 |
| 再平衡 | 每5分钟 |
| 持有期 | 60分钟超时强平 |
| 回撤风控 | DD>8% 清仓 |

---

## 🔌 4. 如何使用自定义策略

核心策略接口已开源，任何人都可以实现自己的策略：

### 步骤 1: 创建策略文件

在项目根目录创建 `my_strategy/` 目录：

```bash
mkdir -p my_strategy
touch my_strategy/__init__.py
```

### 步骤 2: 实现 CoreStrategy 接口

创建 `my_strategy/my_core.py`：

```python
from quantopen.strategy.api import CoreStrategy, StrategyConfig, MarketState, AccountState
from quantopen.strategy import rules, portfolio
import pandas as pd

class MyStrategy(CoreStrategy):
    """你的自定义策略"""
    
    def alpha_score(self, dt, features, hot, themes, market) -> pd.Series:
        # 实现你的打分逻辑
        # 示例：简单动量
        return features.get("ret_1", pd.Series(0.0, index=features.index))
    
    def filter_and_select(self, dt, scores, features, hot, themes, market) -> pd.Series:
        # 实现你的过滤逻辑
        # 使用内置规则
        idx = features.index
        mask = rules.liquidity_mask(features, min_amount_1m=1_000_000)
        out = scores.reindex(idx).where(mask).dropna()
        return out[out > 0].sort_values(ascending=False)
    
    def build_target_weights(self, dt, selected_scores, account, cfg) -> dict:
        # 使用内置组合构建
        weights = portfolio.topk_equal_weight(selected_scores, cfg)
        weights = portfolio.apply_account_risk_control(weights, account, cfg)
        return weights
```

### 步骤 3: 运行回测

```bash
PYTHONPATH=. quantopen backtest-core \
  --core "my_strategy.my_core:MyStrategy" \
  --hotlist-csv data/raw/hotlist.csv \
  --themes-csv data/raw/themes.csv
```

### 可复用模块

| 模块 | 导入路径 | 功能 |
|------|----------|------|
| 过滤规则 | `quantopen.strategy.rules` | 涨停/流动性/热榜过滤 |
| 组合构建 | `quantopen.strategy.portfolio` | TopK等权/风控 |
| 数据下载 | `quantopen.datafeed` | AkShare 分钟线 |
| 回测引擎 | `quantopen.backtest` | Backtrader 封装 |

---

## 📁 项目结构

```
QuantMAx/
├── src/quantopen/
│   ├── cli.py                  # CLI 入口
│   ├── strategy/               # 策略框架 (开源)
│   │   ├── api.py              # CoreStrategy 接口
│   │   ├── rules.py            # 过滤规则
│   │   └── portfolio.py        # 组合构建
│   ├── backtest/               # 回测引擎 (开源)
│   └── datafeed/               # 数据下载 (开源)
├── my_strategy/                # 用户自定义策略
├── configs/                    # 配置文件
└── data/                       # 数据目录
```

---

## ⚙️ 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `topk` | 5 | 最大持仓数 |
| `hot_topn` | 50 | 热榜前N名 |
| `min_amount_1m` | 200万 | 1分钟最小成交额 |
| `hold_minutes` | 60 | 最大持有分钟 |
| `max_account_drawdown` | 8% | 风控阈值 |

---

## License

MIT
