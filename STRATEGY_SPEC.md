# 分钟级多头超短量化策略 —— 策略规格文档

**Strategy Specification v1.0**

---

## 1. 策略定位（Strategy Overview）

**策略类型**

* 市场：A 股
* 方向：多头（Long-only）
* 频率：分钟级（1min bars）
* 风格：情绪 + 趋势驱动的超短线
* 持有期：分钟级至日内（不隔夜为主）

**核心思想**

> 只在"市场注意力高度集中的主线股票"中，用模型挑选最强势的短期机会，并通过严格的过滤与执行纪律控制风险。

---

## 2. 策略目标（Objectives）

* 捕捉 **日内/超短期的确定性波动**
* 避免 A 股常见的：

  * 涨停板流动性陷阱
  * 一字板虚假成交
  * 低流动性滑点放大
* 保证：

  * 可复现
  * 可回测
  * 可实盘执行

---

## 3. 数据输入（Inputs）

### 3.1 行情数据（必须）

* 频率：1 分钟
* 字段：

  * `open`
  * `high`
  * `low`
  * `close`
  * `volume`
  * `amount`
* 数据源：AkShare / 本地缓存 Parquet

### 3.2 情绪数据

* **同花顺热榜**
* 字段：

  * `date`
  * `symbol`
  * `rank`（1 为最热）

### 3.3 主题数据

* 人工维护或半自动生成的主题股票池
* 字段：

  * `symbol`
  * `theme_boost`（非负实数，表示主题权重）

### 3.4 模型分数数据

* Qlib / LGBM / 其他模型生成的分数
* 格式：

  * `datetime`
  * `symbol`
  * `score`

---

## 4. 策略结构（Core Architecture）

策略由 **三层决策系统** 组成，对应代码中的三个核心接口：

```
alpha_score()        # 模型 & 特征打分
filter_and_select() # 交易裁决与过滤
build_target_weights() # 组合与执行
```

---

## 5. 第一层：Alpha 打分层（Alpha Scoring Layer）

### 5.1 功能

> 对每个股票在当前分钟的"短期上涨潜力"进行打分。

### 5.2 输入

* 分钟级特征（features）
* 可选：模型预测分数（Qlib / LGBM）
* 可选：热榜与主题信息

### 5.3 输出

* `alpha_score[symbol] ∈ ℝ`
* 分数仅用于**排序与相对强弱判断**，不是直接交易信号

### 5.4 分数融合逻辑（示意）

```
BaseScore = ModelScore (if available)
          or BaselineMomentumScore

FinalScore = BaseScore
           × HotRankWeight
           × ThemeBoost
```

> **注意**：
>
> * 模型分数优先
> * 模型缺失 → 自动回退到 baseline
> * 融合方式（乘法/加法/阈值）属于闭源核心

---

## 6. 第二层：过滤与裁决层（Filter & Decision Layer）

> 该层决定 **哪些 Alpha 信号"允许"变成交易**。
> 这是策略差异化与稳定性的关键层。

### 6.1 热榜过滤（情绪约束）

* 仅交易：

  * `rank <= hot_topn` 的股票
* 目的：

  * 保证市场注意力
  * 提高成交确定性

### 6.2 涨停过滤（A 股约束）

* 近似判断：

  ```
  (close / prev_close - 1) >= limit_up_threshold → 禁止买入
  ```
* 默认：

  * `limit_up_threshold = 9.5%`
* 目的：

  * 避免涨停板/一字板无法成交

### 6.3 流动性过滤

* 条件：

  ```
  amount_1min >= min_amount_1m
  ```
* 默认：

  * `min_amount_1m = 2,000,000`
* 目的：

  * 控制滑点
  * 避免"看得见吃不到"

### 6.4 分数有效性过滤

* 规则：

  * `alpha_score > 0`
* 目的：

  * 避免噪声交易

---

## 7. 第三层：组合与执行层（Portfolio & Execution）

### 7.1 选股与仓位

* 在通过过滤的股票中：

  * 按 `alpha_score` 排序
  * 选择 TopK
* 默认：

  * `topk = 5`
  * 等权分配
  * 单票最大仓位：`max_weight_per_symbol = 10%`

### 7.2 再平衡节奏

* 每 `rebalance_every_n_minutes` 分钟重新计算
* 默认：

  * `rebalance_every_n_minutes = 5`

### 7.3 持有期控制

* 最大持有时间：

  * `hold_minutes = 60`
* 超时强制卖出
* 目的：

  * 保持"超短线"属性
  * 避免回撤扩大

---

## 8. 风控规则（Risk Control）

### 8.1 账户级回撤控制

* 计算：

  ```
  drawdown = (peak_equity - current_equity) / peak_equity
  ```
* 触发条件：

  ```
  drawdown >= max_account_drawdown
  ```
* 默认：

  * `max_account_drawdown = 8%`

### 8.2 风控动作

* 触发后：

  * 所有目标仓位 → `risk_off_weight`
* 默认：

  * `risk_off_weight = 0.0`（清仓）

---

## 9. 参数总表（StrategyConfig）

| 参数                        | 含义        | 默认值       |
| ------------------------- | --------- | --------- |
| topk                      | 最大持仓股票数   | 5         |
| max_weight_per_symbol     | 单票最大权重    | 0.10      |
| hot_topn                  | 热榜前 N 名   | 50        |
| min_amount_1m             | 1 分钟最小成交额 | 2,000,000 |
| limit_up_threshold        | 涨停近似阈值    | 0.095     |
| rebalance_every_n_minutes | 再平衡周期     | 5         |
| hold_minutes              | 最大持有分钟    | 60        |
| max_account_drawdown      | 账户最大回撤    | 0.08      |
| risk_off_weight           | 风控触发仓位    | 0.0       |

---

## 10. 可扩展方向（Future Extensions）

* 更复杂的分钟级特征（多窗口动量、VWAP 偏离）
* Qlib 深度模型（GRU / Transformer）
* 主题拥挤度与退潮信号
* 分时段规则（开盘/尾盘不同权重）
* 实盘级撮合失败模拟

---

## 11. 非目标（Non-Goals）

* 不做超高频（tick / L2）
* 不追求全市场覆盖
* 不试图预测中长期趋势
* 不依赖单一模型或单一因子

---

## 12. 策略一句话总结（最终版）

> **在 A 股主线题材与热榜股票中，用模型筛选最强分钟级 Alpha 信号，规避涨停与流动性陷阱，按固定节奏做 TopK 多头超短交易，并通过严格风控确保资金安全。**
