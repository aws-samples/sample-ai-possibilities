---
title: "06 Invoke Model With Caching"
date: 2026-02-18
layout: snippet
language: python
description: "06 - Bedrock InvokeModel API + Prompt Caching + AgentCore Code Interpreter

Prompt caching reduces cost and latency when the same system prompt and tool
definitions are sent across multiple calls — a common pattern in agentic
workflows where the model is called repeatedly in a tool-use loop.

How it works:
  1. Mark reusable content (system prompt, tools) with `cache_control`
  2. First call: tokens are written to cache (slightly higher write cost)
  3. Subsequent calls: tokens are read from cache (lower cost, lower latency)

IMPORTANT — When to use caching:
  - USE for content that repeats across calls: system prompts, tool definitions,
    long reference documents, few-shot examples
  - AVOID caching content that changes every call (user messages, dynamic context)
    — cache writes cost MORE than uncached tokens, so caching volatile content
    increases cost without benefit

NOTE: Prompt caching requires a REGIONAL model ID (e.g., us.anthropic.claude-*).
Cross-region model IDs (global.*) route requests to different regions, preventing
cache hits.

Requirements:
    pip install boto3 bedrock-agentcore

Usage:
    python 06_invoke_model_with_caching.py"
source_file: "snippets/migration-from-code-execution-tool-to-agentcore-code-interpreter/06_invoke_model_with_caching.py"
---

# 06 Invoke Model With Caching

06 - Bedrock InvokeModel API + Prompt Caching + AgentCore Code Interpreter

Prompt caching reduces cost and latency when the same system prompt and tool
definitions are sent across multiple calls — a common pattern in agentic
workflows where the model is called repeatedly in a tool-use loop.

How it works:
  1. Mark reusable content (system prompt, tools) with `cache_control`
  2. First call: tokens are written to cache (slightly higher write cost)
  3. Subsequent calls: tokens are read from cache (lower cost, lower latency)

IMPORTANT — When to use caching:
  - USE for content that repeats across calls: system prompts, tool definitions,
    long reference documents, few-shot examples
  - AVOID caching content that changes every call (user messages, dynamic context)
    — cache writes cost MORE than uncached tokens, so caching volatile content
    increases cost without benefit

NOTE: Prompt caching requires a REGIONAL model ID (e.g., us.anthropic.claude-*).
Cross-region model IDs (global.*) route requests to different regions, preventing
cache hits.

Requirements:
    pip install boto3 bedrock-agentcore

Usage:
    python 06_invoke_model_with_caching.py

```python
"""
06 - Bedrock InvokeModel API + Prompt Caching + AgentCore Code Interpreter

Prompt caching reduces cost and latency when the same system prompt and tool
definitions are sent across multiple calls — a common pattern in agentic
workflows where the model is called repeatedly in a tool-use loop.

How it works:
  1. Mark reusable content (system prompt, tools) with `cache_control`
  2. First call: tokens are written to cache (slightly higher write cost)
  3. Subsequent calls: tokens are read from cache (lower cost, lower latency)

IMPORTANT — When to use caching:
  - USE for content that repeats across calls: system prompts, tool definitions,
    long reference documents, few-shot examples
  - AVOID caching content that changes every call (user messages, dynamic context)
    — cache writes cost MORE than uncached tokens, so caching volatile content
    increases cost without benefit

NOTE: Prompt caching requires a REGIONAL model ID (e.g., us.anthropic.claude-*).
Cross-region model IDs (global.*) route requests to different regions, preventing
cache hits.

Requirements:
    pip install boto3 bedrock-agentcore

Usage:
    python 06_invoke_model_with_caching.py
"""

import boto3
import json

# --- Configuration ---
REGION = "us-west-2"

# Caching requires a REGIONAL model ID — cross-region (global.*) won't cache
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

# --- AWS Clients ---
bedrock = boto3.client("bedrock-runtime", region_name=REGION)
agentcore = boto3.client("bedrock-agentcore", region_name=REGION)

# --- System prompt (cached across calls) ---
# Must exceed the minimum token threshold for caching:
#   - 1,024 tokens for Claude Sonnet models
#   - 4,096 tokens for Claude Opus / Haiku models
# This is the IDEAL candidate for caching: it's identical on every call.
SYSTEM_PROMPT = """You are an expert data analyst assistant with deep expertise in statistics,
machine learning, data visualization, and scientific computing. When asked to perform
calculations, statistical analysis, or data processing, always use the execute_python
tool to run Python code and verify your results. Show your work step by step.

You have access to a secure Python sandbox with common libraries pre-installed:
numpy, pandas, matplotlib, scipy, sklearn, seaborn, and all standard library modules.

Guidelines for code execution:
- Always verify calculations with code rather than doing mental math
- Use descriptive variable names in your code for readability
- Print results clearly with labels and formatting
- When working with datasets, provide comprehensive summary statistics including
  count, mean, median, mode, standard deviation, variance, min, max, quartiles,
  skewness, and kurtosis
- For visualizations, use matplotlib or seaborn, save plots to files, and describe
  what the visualizations show about the underlying data patterns
- Handle edge cases gracefully: empty datasets, division by zero, missing values,
  outliers, and non-numeric data
- Use type hints and docstrings when writing functions for clarity
- When performing statistical tests, state the null and alternative hypotheses,
  report the test statistic and p-value, and provide interpretation at standard
  significance levels (0.05, 0.01)
- For machine learning tasks, always split data into train/test sets, report
  appropriate metrics (accuracy, precision, recall, F1, RMSE, MAE, R-squared),
  and discuss potential overfitting or underfitting
- When comparing groups, use appropriate statistical tests (t-test, ANOVA,
  chi-squared, Mann-Whitney U) based on the data distribution and sample size
- Document assumptions made during analysis and flag any data quality issues

Common analysis workflows:
1. Descriptive statistics: summarize central tendency, spread, and shape of distributions
2. Exploratory data analysis: identify patterns, correlations, outliers, and anomalies
3. Hypothesis testing: formulate null and alternative hypotheses, select appropriate tests
4. Regression analysis: model linear and non-linear relationships between variables
5. Classification: predict categorical outcomes using logistic regression, decision trees,
   random forests, gradient boosting, support vector machines, and neural networks
6. Clustering: identify natural groupings using k-means, hierarchical clustering, DBSCAN
7. Time series: analyze trends, seasonality, stationarity, and make forecasts using
   ARIMA, exponential smoothing, and Prophet models
8. Dimensionality reduction: apply PCA, t-SNE, UMAP for visualization and feature selection
9. Feature engineering: create derived features, handle categorical variables, normalize
   and standardize numerical features, handle missing data with imputation strategies
10. Model evaluation: use cross-validation, learning curves, confusion matrices, ROC curves,
    precision-recall curves, and calibration plots to assess model performance

Statistical concepts reference:
- Central tendency: mean (arithmetic, geometric, harmonic), median, mode, trimmed mean
- Dispersion: range, interquartile range (IQR), variance, standard deviation, coefficient
  of variation, mean absolute deviation
- Distribution shape: skewness (positive/negative), kurtosis (leptokurtic/platykurtic),
  normality tests (Shapiro-Wilk, Kolmogorov-Smirnov, Anderson-Darling)
- Correlation: Pearson (linear), Spearman (monotonic), Kendall tau (ordinal),
  point-biserial (binary-continuous), phi coefficient (binary-binary)
- Effect sizes: Cohen's d, Hedges' g, Glass's delta, eta-squared, omega-squared,
  odds ratio, relative risk, number needed to treat
- Confidence intervals: standard normal, t-distribution, bootstrap, Wilson score
- Power analysis: sample size determination, minimum detectable effect, statistical power

Data quality checks to always perform:
- Check for missing values and their patterns (MCAR, MAR, MNAR)
- Identify and handle outliers using IQR method, z-scores, or isolation forests
- Verify data types and ranges for each variable
- Check for duplicate records and inconsistent formatting
- Assess multicollinearity using VIF (variance inflation factor) for regression models
- Test for homoscedasticity and normality of residuals in regression analysis"""

# --- Tool definition with cache_control ---
# Tool definitions are also great candidates for caching — they're identical
# across every call in the agentic loop.
TOOLS = [
    {
        "name": "execute_python",
        "description": (
  "Execute Python code in a secure sandbox environment. "
  "Use this for calculations, data analysis, statistical tests, "
  "or to verify results. Common libraries like numpy, pandas, scipy, "
  "and matplotlib are available. Print output to see results."
        ),
        "input_schema": {
  "type": "object",
  "properties": {
      "code": {
          "type": "string",
          "description": "Python code to execute"
      }
  },
  "required": ["code"]
        },
        # Cache the tool definition — reused on every call in the agentic loop
        "cache_control": {"type": "ephemeral"}
    }
]


def execute_code(code: str, session_id: str) -> str:
    """Execute code via AgentCore and return the output."""
    response = agentcore.invoke_code_interpreter(
        codeInterpreterIdentifier="aws.codeinterpreter.v1",
        sessionId=session_id,
        name="executeCode",
        arguments={"language": "python", "code": code}
    )
    parts = []
    for event in response["stream"]:
        if "result" in event:
  for item in event["result"].get("content", []):
      if item["type"] == "text":
          parts.append(item["text"])
    return "\n".join(parts)


def invoke_with_caching(user_message: str, session_id: str) -> dict:
    """
    Call Claude via InvokeModel with prompt caching.

    The system prompt and tools are cached. Only the user message changes
    between calls — this is the typical pattern in agentic workflows.

    Returns a dict with answer and cache metrics.
    """
    messages = [{"role": "user", "content": [{"type": "text", "text": user_message}]}]

    while True:
        request_body = {
  "anthropic_version": "bedrock-2023-05-31",
  "max_tokens": 4096,
  "system": [
      {
          "type": "text",
          "text": SYSTEM_PROMPT,
          # Cache the system prompt — identical on every call
          "cache_control": {"type": "ephemeral"}
      }
  ],
  "messages": messages,
  "tools": TOOLS
        }

        response = bedrock.invoke_model(
  modelId=MODEL_ID,
  body=json.dumps(request_body),
  contentType="application/json",
  accept="application/json"
        )

        result = json.loads(response["body"].read())

        # Extract cache metrics from usage
        usage = result.get("usage", {})
        cache_write = usage.get("cache_creation_input_tokens", 0)
        cache_read = usage.get("cache_read_input_tokens", 0)
        input_tokens = usage.get("input_tokens", 0)

        messages.append({"role": "assistant", "content": result["content"]})

        if result["stop_reason"] != "tool_use":
  answer = "\n".join(
      b["text"] for b in result["content"] if b["type"] == "text"
  )
  return {
      "answer": answer,
      "cache_write_tokens": cache_write,
      "cache_read_tokens": cache_read,
      "input_tokens": input_tokens,
  }

        # Execute requested tools
        tool_results = []
        for block in result["content"]:
  if block["type"] == "tool_use":
      try:
          output = execute_code(block["input"]["code"], session_id)
          tool_results.append({
              "type": "tool_result",
              "tool_use_id": block["id"],
              "content": [{"type": "text", "text": output}]
          })
      except Exception as e:
          tool_results.append({
              "type": "tool_result",
              "tool_use_id": block["id"],
              "content": [{"type": "text", "text": str(e)}],
              "is_error": True
          })

        messages.append({"role": "user", "content": tool_results})


def main():
    session = agentcore.start_code_interpreter_session(
        codeInterpreterIdentifier="aws.codeinterpreter.v1",
        name="caching-demo",
        sessionTimeoutSeconds=900
    )
    session_id = session["sessionId"]
    print(f"Session: {session_id}\n")

    try:
        # --- Call 1: Cache WRITE ---
        # System prompt + tools are written to cache on the first call.
        # This has a slightly higher token cost than uncached, but pays off
        # on subsequent calls.
        print("=== Call 1: Calculate mean (cache WRITE) ===")
        r1 = invoke_with_caching(
  "Calculate the mean of [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]",
  session_id
        )
        print(f"Answer: {r1['answer'][:200]}")
        print(f"  Cache write: {r1['cache_write_tokens']} tokens")
        print(f"  Cache read:  {r1['cache_read_tokens']} tokens")
        print(f"  Uncached:    {r1['input_tokens']} tokens")

        # --- Call 2: Cache READ ---
        # Same system prompt + tools are read from cache at a reduced rate.
        # Only the user message (new tokens) is processed at full cost.
        print("\n=== Call 2: Calculate std dev (cache READ) ===")
        r2 = invoke_with_caching(
  "Calculate the standard deviation of [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]",
  session_id
        )
        print(f"Answer: {r2['answer'][:200]}")
        print(f"  Cache write: {r2['cache_write_tokens']} tokens")
        print(f"  Cache read:  {r2['cache_read_tokens']} tokens  <-- saved!")
        print(f"  Uncached:    {r2['input_tokens']} tokens")

        # --- Call 3: Another cache READ ---
        print("\n=== Call 3: Calculate median (cache READ) ===")
        r3 = invoke_with_caching(
  "Calculate the median and mode of [1, 2, 2, 3, 4, 5, 5, 5, 9, 10]",
  session_id
        )
        print(f"Answer: {r3['answer'][:200]}")
        print(f"  Cache write: {r3['cache_write_tokens']} tokens")
        print(f"  Cache read:  {r3['cache_read_tokens']} tokens  <-- saved!")
        print(f"  Uncached:    {r3['input_tokens']} tokens")

        # --- Summary ---
        total_cached = r2["cache_read_tokens"] + r3["cache_read_tokens"]
        print(f"\n=== Summary ===")
        print(f"Call 1: wrote {r1['cache_write_tokens']} tokens to cache")
        print(f"Call 2: read  {r2['cache_read_tokens']} tokens from cache")
        print(f"Call 3: read  {r3['cache_read_tokens']} tokens from cache")
        print(f"Total tokens served from cache: {total_cached}")
        print(f"\nIn an agentic loop with many tool-use round-trips, these")
        print(f"savings compound — the system prompt and tools are cached once")
        print(f"and reused on every subsequent call in the loop.")

    finally:
        agentcore.stop_code_interpreter_session(
  codeInterpreterIdentifier="aws.codeinterpreter.v1",
  sessionId=session_id
        )
        print(f"\nSession stopped: {session_id}")


if __name__ == "__main__":
    main()

```

<div class='source-links'>
  <a href='https://github.com/aws-samples/sample-ai-possibilities/blob/main/snippets/migration-from-code-execution-tool-to-agentcore-code-interpreter/06_invoke_model_with_caching.py' class='btn btn-primary'>
    View Raw File
  </a>
</div>
