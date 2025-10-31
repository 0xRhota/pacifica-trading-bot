# Agent Lightning Research: Applicability to Trading Bot

## Executive Summary

**Verdict:** Agent Lightning is promising but premature for our current trading bot stage. Recommend waiting 2-3 months to collect baseline performance data before experimenting.

**Key Findings:**
- Agent Lightning enables training AI agents through Reinforcement Learning with minimal code changes
- Two algorithms available: VERL (model fine-tuning) and APO (prompt optimization)
- APO is more practical for our use case (no GPU required, faster iteration)
- Main challenges: delayed reward signals, market stochasticity, data requirements
- Most promising application: position exit timing optimization (shorter feedback loop)
- Requires 2-3 months of trading history for meaningful training data

**Recommendation:** Continue running current bot, manually analyze performance, revisit Agent Lightning for optimization experiments after establishing baseline edge.

---

## 1. What is Agent Lightning?

Agent Lightning is Microsoft's framework for training AI agents using Reinforcement Learning with (almost) zero code changes. Released in 2025, it aims to make RL accessible for practical agent applications.

**Core Philosophy:**
- Work with ANY agent framework (LangChain, AutoGen, CrewAI, etc.) or raw Python
- Minimal code modifications required
- RL training loop handles the complexity
- Developer focuses on agent logic, not RL plumbing

**Repository:** https://github.com/microsoft/agent-lightning

**Key Statistics:**
- Published paper: [arXiv:2508.03680](https://arxiv.org/abs/2508.03680)
- Active development with CI/CD on multiple examples
- Supports distributed training with Ray
- MIT License

---

## 2. Core Concepts

### 2.1 Architecture Overview

Agent Lightning uses a centralized store architecture with distributed workers:

```
┌─────────────────────────────────────────────────────────┐
│                    LightningStore                       │
│  (Central hub: tasks, resources, traces, rewards)       │
└─────────────────────────────────────────────────────────┘
         ▲                                    ▲
         │ Tasks                    Traces & │
         │                           Rewards │
         ▼                                    │
┌─────────────────┐                 ┌────────┴─────────┐
│   Algorithm     │                 │    Runners       │
│  (Learn & Plan) │◄────Resources───│  (Execute Agent) │
└─────────────────┘                 └──────────────────┘
         │
         │ Updated Resources
         ▼
┌─────────────────────────────────────────────────────────┐
│                     Trainer                              │
│              (Orchestrates Everything)                   │
└─────────────────────────────────────────────────────────┘
```

**Components:**

1. **LightningStore:** Central database storing:
   - Tasks (agent inputs to process)
   - Resources (prompts, model endpoints, weights)
   - Traces (execution logs with spans)
   - Rewards (performance signals)

2. **Runner:** Worker processes that:
   - Pull tasks from store
   - Execute agent rollouts
   - Capture execution traces (spans)
   - Send rewards back to store

3. **Algorithm:** Learning brain that:
   - Reads traces from completed rollouts
   - Analyzes what worked/failed
   - Updates resources (prompts or weights)
   - Enqueues new training tasks

4. **Trainer:** High-level orchestrator that:
   - Coordinates all components
   - Manages training loops
   - Spawns parallel runners
   - Handles datasets and validation

### 2.2 Key Terminology

**Task:** A specific problem instance for the agent to solve.
- Example: "Find a room for 4 people at 10:00 AM with whiteboard"
- In trading: Market state at decision time

**Rollout:** Complete execution of agent attempting one task.
- Example: Full process from receiving task to booking room
- In trading: One complete trading decision cycle

**Span:** Single unit of work within a rollout (OpenTelemetry concept).
- Example: One LLM call, one tool execution, one API request
- In trading: Deep42 query, market data fetch, LLM reasoning

**Reward:** Numeric signal indicating rollout success (typically 0.0 to 1.0).
- Example: 1.0 if room booking correct, 0.0 if wrong
- In trading: P&L percentage, Sharpe ratio

**Resource:** Optimizable asset shared across rollouts.
- Example: Prompt template, model weights, LLM endpoint
- In trading: Trading decision prompt, exit timing prompt

---

## 3. Algorithms Available

### 3.1 VERL (Reinforcement Learning)

**What it does:** Fine-tunes LLM model weights through RL training.

**Key Details:**
- Uses GRPO (Group Relative Policy Optimization) algorithm
- Requires GPU: 40GB+ VRAM (A100 recommended)
- Training time: 12+ hours for moderate-sized models
- Produces improved model checkpoint
- Uses vLLM for fast inference during rollouts
- Distributed training with Ray

**Example Performance:**
- SQL Agent (Spider dataset): 46% → 73% accuracy
- Math Agent (Calc-X): Significant improvement in problem-solving

**Requirements:**
```bash
pip install agentlightning[verl]
# Also needs: PyTorch, CUDA, Ray, vLLM
```

**Configuration:**
```python
verl_config = {
    "algorithm": {"adv_estimator": "grpo"},
    "actor_rollout_ref": {
        "rollout": {"n": 4, "name": "vllm"},
        "model": {"path": "Qwen/Qwen2.5-Coder-1.5B-Instruct"},
    },
    "trainer": {"n_gpus_per_node": 1, "total_epochs": 2}
}
algorithm = agl.VERL(verl_config)
```

**Pros:**
- Most powerful optimization
- Learns deep behavioral patterns
- Can adapt model to specific domain

**Cons:**
- Expensive infrastructure (40GB GPU)
- Long training time (12+ hours)
- Complex setup (Ray, vLLM, PyTorch)
- Requires large training dataset (hundreds of examples)
- Can't use with external APIs (DeepSeek, OpenAI)

### 3.2 APO (Automatic Prompt Optimization)

**What it does:** Optimizes prompt text through LLM-based critique and rewriting.

**Key Details:**
- Uses meta-LLM to critique prompts (GPT-4, Claude, etc.)
- No GPU required (just inference)
- Training time: ~10 minutes
- Produces improved prompt text
- No model weight changes

**Process:**
1. **Evaluate:** Run rollouts with current prompt
2. **Critique:** Meta-LLM analyzes traces and generates "textual gradient" (natural language critique)
3. **Rewrite:** Meta-LLM applies critique to generate improved prompt
4. **Repeat:** Iterate until convergence

**Example Performance:**
- Room Selector: 56% → 72% accuracy (2 rounds, 10 minutes)

**Requirements:**
```bash
pip install agentlightning[apo]
# Needs: OpenAI API key or other LLM for meta-optimization
```

**Configuration:**
```python
from openai import AsyncOpenAI

openai_client = AsyncOpenAI()
algorithm = agl.APO(
    openai_client,
    gradient_batch_size=4,  # Rollouts to critique
    beam_width=2,           # Prompt variants to explore
    branch_factor=2         # Exploration breadth
)
```

**Pros:**
- Lightweight (no GPU needed)
- Fast iterations (minutes not hours)
- Works with any LLM API (DeepSeek, OpenAI, etc.)
- Human-readable improvements (can review prompt changes)
- Smaller data requirements

**Cons:**
- Less powerful than VERL (surface-level optimization)
- Depends on meta-LLM quality
- Can't change model behavior fundamentally

### 3.3 Algorithm Comparison

| Feature | VERL | APO |
|---------|------|-----|
| **What's optimized** | Model weights | Prompt text |
| **GPU required** | Yes (40GB+) | No |
| **Training time** | 12+ hours | ~10 minutes |
| **Setup complexity** | High (Ray, vLLM) | Low (just API key) |
| **Data requirements** | Hundreds of examples | Tens of examples |
| **Works with APIs** | No (needs model access) | Yes (any LLM) |
| **Optimization depth** | Deep behavioral changes | Surface-level changes |
| **Result format** | Model checkpoint | Text file (prompt) |
| **Cost** | GPU hours ($$$) | LLM API calls ($) |

**For our trading bot:** APO is more practical given our constraints.

---

## 4. How Agent Lightning Works

### 4.1 Training Loop

The core training loop coordinates tasks, rollouts, and learning:

```python
# Conceptual flow (simplified)

# 1. Algorithm enqueues tasks
algorithm.generate_tasks(dataset) → LightningStore

# 2. Runners execute tasks
while store.has_tasks():
    task = store.pull_task()
    reward = agent.rollout(task, resources)
    trace = capture_execution_spans()
    store.push_result(trace, reward)

# 3. Algorithm learns from results
traces_and_rewards = store.get_results()
new_resources = algorithm.learn(traces_and_rewards)
store.update_resources(new_resources)

# 4. Repeat with improved resources
```

### 4.2 Minimal Integration Pattern

The simplest integration uses the `@rollout` decorator:

```python
import agentlightning as agl

@agl.rollout
def my_agent(task: Dict, prompt_template: agl.PromptTemplate) -> float:
    """
    Agent logic that Agent Lightning will optimize.

    Args:
        task: Input data (e.g., market conditions)
        prompt_template: Prompt to use (APO optimizes this)

    Returns:
        reward: Performance metric (0.0 to 1.0)
    """
    # Format prompt with task data
    prompt = prompt_template.format(
        symbol=task["symbol"],
        price=task["price"],
        # ... other variables
    )

    # Call LLM to make decision
    decision = llm.call(prompt)

    # Execute action and evaluate
    outcome = execute_action(decision)
    reward = calculate_reward(outcome)

    return reward

# Training
trainer = agl.Trainer(
    algorithm=agl.APO(openai_client),
    initial_resources={
        "prompt_template": agl.PromptTemplate(
            template="You are a trading bot. Symbol: {symbol}...",
            engine="f-string"
        )
    }
)

trainer.fit(
    agent=my_agent,
    train_dataset=training_data,
    val_dataset=validation_data
)
```

### 4.3 Distributed Execution

Agent Lightning can run multiple agent workers in parallel:

```python
trainer = agl.Trainer(
    algorithm=algorithm,
    n_runners=10,  # 10 parallel workers
)
```

Each runner:
- Pulls tasks independently
- Executes rollouts concurrently
- Sends traces back to central store
- Enables faster training through parallelism

---

## 5. Potential Applications to Trading Bot

### 5.1 Current Bot Architecture

Our LLM trading bot currently operates as:

```python
# Current flow (simplified)
while True:
    # Gather context
    macro = get_deep42_macro()
    token_analyses = get_deep42_token_analyses(selected_tokens)
    market_data = get_pacifica_market_data()

    # Format hardcoded prompt
    prompt = f"""
    You are a trading bot. Here is the macro context:
    {macro}

    Selected token analyses:
    {token_analyses}

    Market data:
    {market_data}

    Decision: BUY, SELL, HOLD, or CLOSE?
    """

    # Get LLM decision
    decision = deepseek.call(prompt)

    # Execute
    if decision.action == "BUY":
        execute_buy(decision.symbol, decision.amount)

    # Sleep 5 minutes
    time.sleep(300)
```

### 5.2 Use Case 1: Full Trading Decision Optimization (Not Recommended)

**Concept:** Optimize prompts for the entire trading decision.

**Implementation:**
```python
@agl.rollout
def trading_agent(task: Dict, prompt_template: agl.PromptTemplate) -> float:
    # task = {timestamp, symbol, market_data, macro_context, ...}

    prompt = prompt_template.format(**task)
    decision = llm.call(prompt)

    if decision.action == "BUY":
        entry_price = execute_buy(task["symbol"])
        # ... WAIT FOR EXIT (hours/days) ...
        exit_price = wait_for_exit()
        reward = (exit_price - entry_price) / entry_price
    else:
        reward = 0.0

    return reward
```

**Challenges:**
- ❌ **Delayed rewards:** Must wait hours/days for trade to complete
- ❌ **Data collection:** Need hundreds of completed trades (months of data)
- ❌ **Market stochasticity:** Same decision can lead to profit or loss randomly
- ❌ **Live trading risk:** Can't do exploratory trades just for training

**Verdict:** Too difficult for initial application.

### 5.3 Use Case 2: Position Exit Timing Optimization (Recommended)

**Concept:** Given an open position, optimize decision of when to close it.

**Implementation:**
```python
@agl.rollout
def exit_timing_agent(task: Dict, prompt_template: agl.PromptTemplate) -> float:
    # task = {
    #     symbol, entry_price, current_price,
    #     time_held_minutes, pnl_pct,
    #     current_market_data, sentiment
    # }

    prompt = prompt_template.format(**task)
    decision = llm.call(prompt)  # "CLOSE" or "HOLD"

    if decision == "CLOSE":
        exit_price = execute_close(task["symbol"])
        reward = (exit_price - task["entry_price"]) / task["entry_price"]
    else:
        # Wait 15 minutes and check again
        time.sleep(900)
        later_price = get_price(task["symbol"])
        reward = (later_price - task["entry_price"]) / task["entry_price"]

    return reward
```

**Benefits:**
- ✅ **Shorter feedback loop:** Minutes to hours, not days
- ✅ **Clear reward signal:** Actual P&L vs hypothetical
- ✅ **Less risky:** Optimizing exit on existing positions
- ✅ **More data:** Multiple exit decisions per trade
- ✅ **Focused problem:** Easier to learn patterns

**Training Data:**
Can extract from our trade logs:
```python
# Each entry in logs becomes a training example
{
    "symbol": "SOL",
    "entry_price": 182.50,
    "exit_price": 185.20,  # actual outcome
    "time_held": 45,  # minutes
    "pnl_pct": 1.48,
    "market_data_at_exit_decision": {...},
    "sentiment_at_exit_decision": {...}
}
```

**Verdict:** Most promising initial application.

### 5.4 Use Case 3: Risk Management Optimization

**Concept:** Optimize position sizing and stop-loss placement.

**Implementation:**
```python
@agl.rollout
def risk_manager_agent(task: Dict, prompt_template: agl.PromptTemplate) -> float:
    # task = {
    #     symbol, account_balance, volatility,
    #     recent_win_rate, open_positions
    # }

    prompt = prompt_template.format(**task)
    decision = llm.call(prompt)
    # Returns: position_size_usd, stop_loss_pct, take_profit_pct

    # Execute trade with these parameters
    outcome = execute_trade_with_params(decision)

    # Reward: risk-adjusted return (Sharpe-like metric)
    reward = outcome.pnl / outcome.max_drawdown

    return reward
```

**Benefits:**
- ✅ **Clear success metric:** Risk-adjusted returns
- ✅ **Generalizable:** Works across all symbols
- ✅ **Safe experimentation:** Can test in simulation

**Challenges:**
- ⚠️ **Still delayed feedback:** Need to see full trade lifecycle
- ⚠️ **Complex reward design:** Balancing risk vs return

**Verdict:** Interesting but secondary priority.

### 5.5 Use Case 4: Token Selection Optimization

**Concept:** Optimize which 3 tokens to analyze each cycle.

**Current approach:** LLM freely chooses 3 tokens from 218 available

**Optimized approach:**
```python
@agl.rollout
def token_selector_agent(task: Dict, prompt_template: agl.PromptTemplate) -> float:
    # task = {available_tokens: [...], macro_context: {...}}

    prompt = prompt_template.format(**task)
    selected = llm.call(prompt)  # Returns 3 token symbols

    # Analyze selected tokens
    analyses = get_deep42_analyses(selected)

    # Make trading decision
    decision = trading_decision_with_analyses(analyses)

    # Reward: 1.0 if profitable trade, 0.0 if no trade or loss
    reward = 1.0 if decision.was_profitable else 0.0

    return reward
```

**Benefits:**
- ✅ **Clear optimization target:** Which tokens lead to good trades
- ✅ **Fast iteration:** Can test many combinations

**Challenges:**
- ⚠️ **Attribution problem:** Was profit due to token selection or market luck?
- ⚠️ **Sparse reward:** Only profitable trades give positive signal

**Verdict:** Interesting but low priority.

---

## 6. Challenges and Limitations

### 6.1 Delayed Reward Problem

**Issue:** Trading rewards are not immediate like in Agent Lightning examples.

**Examples with immediate rewards:**
- SQL query: Know if correct instantly
- Room booking: Know if right room immediately
- Math problem: Calculate correct answer instantly

**Trading reality:**
- Position opened → Wait hours/days → Position closed → Know P&L
- During wait, market moves randomly
- Hard to attribute success to decision quality vs luck

**Potential solutions:**
- Focus on shorter-timeframe decisions (exit timing)
- Use proxy rewards (e.g., "is decision aligned with trend?")
- Accept longer training cycles

### 6.2 Market Stochasticity

**Issue:** Same decision can lead to profit or loss due to random market movements.

**Example:**
- Day 1: Buy SOL at $180, news breaks, exits at $185 (+2.7%)
- Day 2: Buy SOL at $180, identical reasoning, whale dumps, exits at $175 (-2.7%)

**Impact:**
- Noisy reward signals
- Difficult to learn consistent patterns
- Risk of overfitting to noise

**Potential solutions:**
- Aggregate rewards over many trades
- Use risk-adjusted metrics (Sharpe ratio)
- Focus on process quality, not outcome

### 6.3 Data Requirements

**Issue:** Need significant training data for meaningful optimization.

**Agent Lightning examples:**
- SQL Agent: Thousands of query examples
- Room Selector: Hundreds of booking scenarios
- Math Agent: Thousands of problems

**Our reality:**
- Bot makes ~1 trade per hour
- ~24 trades per day
- ~720 trades per month
- Need 2-3 months minimum for APO training data

**Verdict:** Must run bot longer before attempting optimization.

### 6.4 Live Trading Risk

**Issue:** Can't do exploratory "bad" trades just to collect training data.

**RL typically requires exploration:**
- Try random actions to discover what works
- Accept short-term losses for long-term learning

**Trading constraints:**
- Every bad trade costs real money
- Can't afford random exploration
- Must be profitable from day 1

**Potential solutions:**
- Train on historical data (backtest)
- Use paper trading for exploration
- Conservative exploration in live trading

### 6.5 Overfitting to Historical Data

**Issue:** Optimizing on past trades may not generalize to future markets.

**Risk:**
- Find patterns specific to training period
- Market regime changes (bull → bear)
- Strategies stop working when deployed

**Example:**
- Train on bull market data
- Optimize for "buy the dip" prompts
- Deploy in bear market → losses

**Potential solutions:**
- Train on diverse market conditions
- Use walk-forward validation
- Monitor for distribution shift

### 6.6 The Fundamental Edge Problem

**Critical insight:** Agent Lightning can optimize execution, but won't create alpha if the underlying strategy has no edge.

**What Agent Lightning can do:**
- Make prompts clearer and more effective
- Learn which market conditions favor which tactics
- Optimize risk management and position sizing

**What Agent Lightning cannot do:**
- Overcome efficient market hypothesis
- Predict future prices with no signal
- Make unprofitable strategy profitable through prompt tuning

**Implication:** Must first validate that bot has baseline edge before optimizing.

---

## 7. Implementation Requirements

### 7.1 For APO (Recommended Path)

**Infrastructure:**
```bash
# Python environment
python >= 3.10

# Installation
pip install agentlightning[apo]
pip install openai  # For meta-LLM

# API Keys needed
export OPENAI_API_KEY="..."  # For prompt optimization
# (or use Claude, etc.)
```

**Code Changes:**
1. Wrap trading logic in `@agl.rollout` decorator
2. Convert hardcoded prompts to `PromptTemplate` objects
3. Create training dataset from historical trades
4. Implement reward calculation function
5. Set up `Trainer` and run `trainer.fit()`

**Estimated Development Effort:** 2-3 days

**Sample Integration:**
```python
# Step 1: Define agent with decorator
@agl.rollout
def exit_agent(task: Dict, prompt_template: agl.PromptTemplate) -> float:
    prompt = prompt_template.format(**task)
    decision = llm.call(prompt)
    reward = calculate_reward(decision, task)
    return reward

# Step 2: Create initial prompt template
initial_prompt = agl.PromptTemplate(
    template="""
    You are managing an open {symbol} position.
    Entry: ${entry_price}, Current: ${current_price}
    Time held: {time_held} minutes, P&L: {pnl_pct}%

    Market sentiment: {sentiment}
    Technical: RSI={rsi}, MACD={macd}

    Should you CLOSE now or HOLD? Think step by step.
    """,
    engine="f-string"
)

# Step 3: Prepare training data from logs
training_data = load_historical_trades("logs/past_trades.json")

# Step 4: Set up trainer
from openai import AsyncOpenAI

trainer = agl.Trainer(
    algorithm=agl.APO(AsyncOpenAI()),
    n_runners=4,  # Parallel rollouts
    initial_resources={"prompt_template": initial_prompt}
)

# Step 5: Train
trainer.fit(
    agent=exit_agent,
    train_dataset=training_data[:500],
    val_dataset=training_data[500:]
)

# Step 6: Get optimized prompt
optimized_prompt = trainer.get_best_resources()["prompt_template"]
print("Optimized prompt:", optimized_prompt.template)
```

### 7.2 For VERL (Not Recommended)

**Infrastructure:**
```bash
# Requires GPU server
CUDA-enabled machine with 40GB+ VRAM (A100, A6000, etc.)

# Installation
pip install agentlightning[verl]
# Plus: PyTorch, Ray, vLLM (complex setup)

# Ray cluster
ray start --head
```

**Estimated Development Effort:** 1-2 weeks

**Verdict:** Too resource-intensive for our current needs.

---

## 8. Recommendations

### 8.1 Short-term (Next 1-2 Months)

**Do NOT integrate Agent Lightning yet.**

**Focus on:**
1. **Run current bot continuously** to collect 2-3 months of trading data
2. **Manual analysis** of what prompts/decisions lead to profits
3. **Iterate on strategy** based on observed patterns
4. **Track detailed logs** for future training data:
   - Market conditions at decision time
   - LLM reasoning
   - Actual outcomes (P&L, duration)
5. **Document patterns** that work vs don't work

**Why wait:**
- Need baseline performance data
- Must validate bot has an edge
- Need training dataset (hundreds of trades)
- Premature optimization wastes time

### 8.2 Medium-term (2-3 Months Out)

**If bot shows promise, experiment with Agent Lightning APO:**

**Phase 1: Data Preparation**
1. Extract historical trades from logs
2. Reconstruct market state at each decision point
3. Label with actual P&L outcomes
4. Split into train/validation sets (80/20)

**Phase 2: Focused Experiment**
1. Start with **position exit timing** only (shortest feedback loop)
2. Implement `@agl.rollout` wrapper for exit decisions
3. Run APO training offline on historical data
4. Validate: Check if optimized prompts perform better on held-out data

**Phase 3: Backtesting**
1. Run backtest with optimized exit prompts
2. Compare performance vs baseline exit strategy
3. Analyze: Does optimization generalize to new data?

**Phase 4: Paper Trading**
1. Deploy optimized prompts in paper trading mode
2. Run for 1 week alongside live bot
3. Compare results

**Phase 5: Live Deployment**
1. If paper trading successful, deploy to live trading
2. Monitor closely for first week
3. Revert if performance degrades

**Timeline:** 2-3 weeks of experimentation

### 8.3 Long-term (Future Research)

**Advanced applications (6+ months out):**

1. **Multi-agent optimization:**
   - Separate agents for entry vs exit
   - Optimize each independently
   - Coordinate decisions

2. **Market regime detection:**
   - Different prompts for bull/bear/sideways markets
   - Agent learns when to use which prompt

3. **Risk management optimization:**
   - Optimize position sizing
   - Optimize stop-loss placement
   - Maximize Sharpe ratio

4. **Integrated backtesting framework:**
   - Simulation environment for safe exploration
   - Rapid iteration on strategies
   - Validation before live deployment

5. **Portfolio optimization:**
   - Multi-symbol coordination
   - Correlation-aware position sizing
   - Risk budget allocation

### 8.4 Decision Framework

**When to consider Agent Lightning:**

✅ **Yes, if:**
- Bot has 2+ months of trading history
- Clear patterns emerge in successful vs failed trades
- Have 100+ completed trades for training
- Strategy shows baseline profitability
- Team has bandwidth for 2-3 week experiment

❌ **No, if:**
- Less than 1 month of data
- Strategy not yet validated
- No clear optimization target
- Higher priority work to do
- Lack of experimentation infrastructure

---

## 9. Code Examples

### 9.1 Minimal Integration Example

```python
"""
Minimal Agent Lightning integration for exit timing optimization.
"""

import agentlightning as agl
from openai import AsyncOpenAI
from typing import Dict

# Define agent logic
@agl.rollout
def exit_timing_agent(
    task: Dict,
    prompt_template: agl.PromptTemplate
) -> float:
    """
    Decides whether to close an open position.

    Args:
        task: {
            symbol: str,
            entry_price: float,
            current_price: float,
            time_held_minutes: int,
            pnl_pct: float,
            rsi: float,
            macd: float,
            sentiment: str
        }
        prompt_template: Prompt to optimize

    Returns:
        reward: Actual P&L if closed, or P&L after waiting
    """
    # Format prompt with task data
    prompt = prompt_template.format(**task)

    # Get LLM decision
    decision = call_deepseek(prompt)  # Returns "CLOSE" or "HOLD"

    # Execute and calculate reward
    if decision == "CLOSE":
        exit_price = execute_close_position(task["symbol"])
        reward = (exit_price - task["entry_price"]) / task["entry_price"]
    else:
        # Wait 15 minutes and check P&L
        time.sleep(900)
        later_price = get_current_price(task["symbol"])
        reward = (later_price - task["entry_price"]) / task["entry_price"]

    return reward


# Initial prompt template
initial_prompt = agl.PromptTemplate(
    template="""
You are managing an open {symbol} position.

Position details:
- Entry price: ${entry_price}
- Current price: ${current_price}
- Time held: {time_held_minutes} minutes
- Current P&L: {pnl_pct}%

Market indicators:
- RSI: {rsi}
- MACD: {macd}
- Sentiment: {sentiment}

Decision: Should you CLOSE this position now or HOLD?

Respond with just "CLOSE" or "HOLD" and brief reasoning.
    """.strip(),
    engine="f-string"
)


# Load training data
def load_training_data():
    """Load historical trades from logs."""
    import json

    with open("logs/closed_trades.json") as f:
        trades = json.load(f)

    # Convert to task format
    tasks = []
    for trade in trades:
        tasks.append({
            "symbol": trade["symbol"],
            "entry_price": trade["entry_price"],
            "current_price": trade["exit_price"],  # What it was at exit
            "time_held_minutes": trade["duration_minutes"],
            "pnl_pct": trade["pnl_pct"],
            "rsi": trade["rsi_at_exit"],
            "macd": trade["macd_at_exit"],
            "sentiment": trade["sentiment_at_exit"]
        })

    return tasks


# Set up training
def train_exit_agent():
    """Train exit timing agent with APO."""

    # Load data
    all_tasks = load_training_data()
    train_tasks = all_tasks[:int(0.8 * len(all_tasks))]
    val_tasks = all_tasks[int(0.8 * len(all_tasks)):]

    print(f"Training on {len(train_tasks)} trades")
    print(f"Validating on {len(val_tasks)} trades")

    # Set up trainer
    trainer = agl.Trainer(
        algorithm=agl.APO(
            AsyncOpenAI(),
            gradient_batch_size=4,
            beam_width=2,
            branch_factor=2
        ),
        n_runners=4,  # 4 parallel workers
        initial_resources={"prompt_template": initial_prompt}
    )

    # Train
    print("Starting training...")
    trainer.fit(
        agent=exit_timing_agent,
        train_dataset=train_tasks,
        val_dataset=val_tasks
    )

    # Get optimized prompt
    optimized = trainer.get_best_resources()["prompt_template"]

    print("\n=== OPTIMIZED PROMPT ===")
    print(optimized.template)

    # Save to file
    with open("optimized_exit_prompt.txt", "w") as f:
        f.write(optimized.template)

    print("\nSaved to optimized_exit_prompt.txt")


if __name__ == "__main__":
    train_exit_agent()
```

### 9.2 Dry-Run Testing Example

Before full training, test agent logic with `trainer.dev()`:

```python
def test_agent_logic():
    """Test agent without full training loop."""

    # Use smaller dataset
    test_tasks = load_training_data()[:10]

    # Set up trainer with dev mode
    trainer = agl.Trainer(
        n_runners=1,  # Single worker for debugging
        initial_resources={
            "prompt_template": initial_prompt,
            "main_llm": agl.LLM(
                endpoint=os.environ["DEEPSEEK_API_BASE"],
                model="deepseek-chat",
                sampling_parameters={"temperature": 0.7}
            )
        }
    )

    # Dry-run: Execute tasks but don't train
    print("Running dry-run...")
    trainer.dev(
        agent=exit_timing_agent,
        dev_dataset=test_tasks
    )

    print("Dry-run complete. Check spans and rewards above.")
```

### 9.3 Historical Data Extraction Example

```python
def extract_training_data_from_logs():
    """
    Extract training data from bot logs.

    Reads logs/llm_bot.log and extracts closed trades
    with their context and outcomes.
    """
    import re
    import json

    trades = []

    with open("logs/llm_bot.log") as f:
        for line in f:
            # Look for trade closure logs
            if "POSITION CLOSED" in line:
                # Parse log entry
                match = re.search(
                    r"Symbol: (\w+), Entry: ([\d.]+), Exit: ([\d.]+), "
                    r"P&L: ([-\d.]+)%, Duration: (\d+)min",
                    line
                )
                if match:
                    symbol, entry, exit, pnl, duration = match.groups()

                    # Get market context at exit time
                    # (would need to reconstruct from earlier log entries)
                    context = get_market_context_at_time(
                        symbol,
                        line_timestamp
                    )

                    trades.append({
                        "symbol": symbol,
                        "entry_price": float(entry),
                        "exit_price": float(exit),
                        "pnl_pct": float(pnl),
                        "duration_minutes": int(duration),
                        **context
                    })

    # Save as training dataset
    with open("training_data/historical_trades.json", "w") as f:
        json.dump(trades, f, indent=2)

    print(f"Extracted {len(trades)} completed trades")
    return trades
```

---

## 10. Alternative Approaches

If Agent Lightning seems too complex, consider these simpler alternatives:

### 10.1 Manual Prompt A/B Testing

```python
# Define multiple prompt variants
prompts = {
    "conservative": "...focus on capital preservation...",
    "aggressive": "...maximize returns...",
    "balanced": "...balance risk and reward..."
}

# Run each for 1 week
for name, prompt in prompts.items():
    deploy_bot_with_prompt(prompt)
    run_for_days(7)
    results[name] = measure_performance()

# Select best
best_prompt = max(results, key=lambda k: results[k].sharpe_ratio)
```

**Pros:** Simple, no dependencies
**Cons:** Slow (weeks per iteration), limited exploration

### 10.2 Reward-Weighted Random Selection

```python
# Track prompt performance
prompt_scores = {
    "version_1": {"wins": 10, "losses": 5},
    "version_2": {"wins": 15, "losses": 3},
    "version_3": {"wins": 8, "losses": 8}
}

# Select prompt with probability proportional to win rate
def select_prompt():
    weights = [
        p["wins"] / (p["wins"] + p["losses"])
        for p in prompt_scores.values()
    ]
    return random.choices(list(prompt_scores.keys()), weights=weights)[0]
```

**Pros:** Gradual learning, simple
**Cons:** Slower than APO, not sophisticated

### 10.3 LLM-based Self-Reflection

```python
# After trading session
past_decisions = load_last_n_trades(20)

reflection_prompt = f"""
You made these trading decisions recently:
{past_decisions}

Outcomes:
- Wins: {count_wins(past_decisions)}
- Losses: {count_losses(past_decisions)}
- Common winning patterns: {analyze_wins(past_decisions)}
- Common losing patterns: {analyze_losses(past_decisions)}

Your current decision-making prompt is:
{current_prompt}

How could the prompt be improved based on what worked and didn't work?
Suggest specific edits.
"""

suggested_improvements = llm.call(reflection_prompt)
# Manually review and apply
```

**Pros:** Keeps human in loop, no framework needed
**Cons:** Manual work, not systematic

---

## 11. References

### 11.1 Agent Lightning Resources

**Official:**
- Repository: https://github.com/microsoft/agent-lightning
- Documentation: https://microsoft.github.io/agent-lightning/
- Paper: https://arxiv.org/abs/2508.03680 (Agent Lightning: Train ANY AI Agents with Reinforcement Learning)
- Discord: https://discord.gg/RYk7CdvDR7

**Examples:**
- SQL Agent (VERL): `/examples/spider/`
- Room Selector (APO): `/examples/apo/`
- Math Agent (AutoGen): `/examples/calc_x/`

**Blog Posts:**
- [No More Retokenization Drift](https://blog.vllm.ai/2025/10/22/agent-lightning.html) - vLLM blog
- [Training AI Agents to Write and Self-correct SQL](https://medium.com/@yugez/training-ai-agents-to-write-and-self-correct-sql-with-reinforcement-learning-571ed31281ad) - Medium

### 11.2 Reinforcement Learning Concepts

**RL Fundamentals:**
- Sutton & Barto, "Reinforcement Learning: An Introduction"
- OpenAI Spinning Up in Deep RL: https://spinningup.openai.com/

**Policy Optimization:**
- GRPO: Group Relative Policy Optimization
- PPO: Proximal Policy Optimization (foundation of GRPO)

**Challenges in RL:**
- Temporal credit assignment problem
- Exploration vs exploitation tradeoff
- Reward shaping and sparse rewards

### 11.3 Trading-Specific Considerations

**RL in Trading:**
- Most RL-trading research focuses on continuous state/action spaces
- Challenges: non-stationarity, delayed rewards, transaction costs
- Debate: Does RL have edge over traditional methods in efficient markets?

**Prompt Engineering for Trading:**
- Chain-of-thought reasoning for decision explanation
- Few-shot examples for consistent formatting
- Temperature tuning for exploration vs exploitation

---

## 12. Conclusion

Agent Lightning is a sophisticated framework that makes agent training through RL accessible with minimal code changes. For our trading bot:

**Key Takeaways:**

1. **APO is more practical than VERL** for our constraints (no GPU, using API LLMs)

2. **Position exit timing is the most promising initial application** due to shorter feedback loops

3. **Premature for immediate integration** - need 2-3 months of baseline data first

4. **Main challenges:**
   - Delayed reward signals in trading
   - Market stochasticity creates noisy learning signal
   - Data requirements (hundreds of trades)
   - Risk of overfitting to historical data

5. **Agent Lightning won't create alpha** - it can optimize execution, but won't overcome lack of fundamental edge

6. **Recommended path:**
   - Continue running bot to collect data
   - Manually analyze patterns
   - In 2-3 months, experiment with APO for exit timing
   - Validate thoroughly before live deployment

**Final Verdict:** Promising tool for future optimization experiments, but not ready for immediate use. Focus on establishing baseline performance first.

---

**Document Version:** 1.0
**Date:** January 30, 2025
**Author:** Claude (Research Agent)
**Status:** Complete - Ready for review
