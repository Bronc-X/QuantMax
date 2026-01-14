# 规格文档 → 代码逐条映射（SPEC_TO_CODE_MAP）

## 0. 总览：规格三层架构 ⇄ 代码三接口

| 规格层级      | 规格描述                 | 代码入口                                  | 实现位置（闭源/开源）                                                                               |
| --------- | -------------------- | ------------------------------------- | ----------------------------------------------------------------------------------------- |
| Alpha 打分层 | `alpha_score()` 生成分数 | `CoreStrategy.alpha_score()`          | **闭源** `quant_core/core_strategy.py::MyCoreStrategy.alpha_score`                          |
| 过滤与裁决层    | 热榜/涨停/流动性/有效性过滤      | `CoreStrategy.filter_and_select()`    | **闭源** `quant_core/core_strategy.py::MyCoreStrategy.filter_and_select`（用开源 rule）          |
| 组合与执行层    | TopK 等权 + 风控动作       | `CoreStrategy.build_target_weights()` | **闭源** `quant_core/core_strategy.py::MyCoreStrategy.build_target_weights`（调用开源 portfolio） |

开源框架负责：数据、回测撮合、成本、日志、报表与加载闭源策略。

---

## 1. 策略定位（Strategy Overview）

### 1.1 A股 / 多头 / 1min / 超短

* **Backtest 引擎**：`src/quantopen/backtest/`

  * `bt_data.py`：分钟线数据 feed（parquet → bt）
  * `bt_core_strategy.py`：按分钟触发策略 `next()`
  * `run_core.py`：组装 cerebro、装载数据与策略

### 1.2 "分钟级至日内，不隔夜为主"

* **持有期控制（hold_minutes）**

  * 规格：`hold_minutes`
  * 代码：`StrategyConfig.hold_minutes` + `CoreStrategyBT._entry_times` 超时平仓

---

## 2. 数据输入（Inputs）

### 2.1 分钟行情（open/high/low/close/volume/amount）

| 规格字段 | 代码位置 |
|---------|---------|
| 采集 | `datafeed/akshare_1m.py::fetch_1m_eastmoney` |
| 缓存 | `datafeed/cache.py::{read_symbol, write_symbol}` |
| 回测读取 | `backtest/bt_data.py::load_symbol_parquet` |

### 2.2 同花顺热榜（date,symbol,rank）

| 规格字段 | 代码位置 |
|---------|---------|
| 读取 | `bt_core_strategy.py::_load_hot` |
| 当天切片 | `_get_hot_for_day` |

### 2.3 主题数据（symbol, theme_boost）

| 规格字段 | 代码位置 |
|---------|---------|
| 读取 | `bt_core_strategy.py::_load_themes` |
| 融合 | 闭源 `alpha_score` |

---

## 3. 三层决策 → 代码映射

### 3.1 Alpha 打分层

```
CoreStrategy.alpha_score() → pd.Series(index=symbol)
```

### 3.2 过滤与裁决层

| 过滤规则 | 代码函数 |
|---------|---------|
| 热榜过滤 | `rules.hot_rank_mask(cfg.hot_topn)` |
| 涨停过滤 | `rules.approx_limit_up_mask(cfg.limit_up_threshold)` |
| 流动性过滤 | `rules.liquidity_mask(cfg.min_amount_1m)` |
| 分数有效性 | `out[out > 0]` |

### 3.3 组合与执行层

| 规则 | 代码函数 |
|------|---------|
| TopK等权 | `portfolio.topk_equal_weight(cfg)` |
| 风控 | `portfolio.apply_account_risk_control(cfg)` |
| 超时平仓 | `CoreStrategyBT._check_hold_timeout(cfg.hold_minutes)` |

---

## 4. 参数总表（StrategyConfig）⇄ 代码字段

| 规格参数 | 代码字段 | 状态 |
|---------|---------|------|
| topk | `StrategyConfig.topk` | ✅ |
| max_weight_per_symbol | `StrategyConfig.max_weight_per_symbol` | ✅ |
| hot_topn | `StrategyConfig.hot_topn` | ✅ |
| min_amount_1m | `StrategyConfig.min_amount_1m` | ✅ |
| limit_up_threshold | `StrategyConfig.limit_up_threshold` | ✅ |
| rebalance_every_n_minutes | `StrategyConfig.rebalance_every_n_minutes` | ✅ |
| hold_minutes | `StrategyConfig.hold_minutes` | ✅ |
| max_account_drawdown | `StrategyConfig.max_account_drawdown` | ✅ |
| risk_off_weight | `StrategyConfig.risk_off_weight` | ✅ |

---

## 5. 闭源边界

### 开源（公开）
- `src/quantopen/strategy/api.py`
- `src/quantopen/strategy/rules.py`
- `src/quantopen/strategy/portfolio.py`
- `src/quantopen/backtest/*`

### 闭源（不提交）
- `quant_core/core_strategy.py`
