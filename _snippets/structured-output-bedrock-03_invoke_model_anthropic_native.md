---
title: "03 Invoke Model Anthropic Native"
date: 2026-10-15
layout: snippet
language: python
description: "Structured output via InvokeModel, using Anthropic's native output_config field.

Anthropic-only, same mechanism as 02_converse_anthropic_native.py but sent
directly in the InvokeModel request body (the Anthropic Messages shape)."
source_file: "snippets/structured-output-bedrock/03_invoke_model_anthropic_native.py"
---

# 03 Invoke Model Anthropic Native

Structured output via InvokeModel, using Anthropic's native output_config field.

Anthropic-only, same mechanism as 02_converse_anthropic_native.py but sent
directly in the InvokeModel request body (the Anthropic Messages shape).

```python
"""Structured output via InvokeModel, using Anthropic's native output_config field.

Anthropic-only, same mechanism as 02_converse_anthropic_native.py but sent
directly in the InvokeModel request body (the Anthropic Messages shape).
"""
import json
import boto3

REGION = "us-east-1"
MODEL_ID = "us.anthropic.claude-sonnet-5-5"
PROMPT = "Extract the person from: John Smith is 42 years old."
SCHEMA = {
    "type": "object",
    "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
    "required": ["name", "age"],
    "additionalProperties": False,
}

client = boto3.client("bedrock-runtime", region_name=REGION)

body = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 64,
    "messages": [{"role": "user", "content": PROMPT}],
    "output_config": {"format": {"type": "json_schema", "schema": SCHEMA}},
}

response = client.invoke_model(modelId=MODEL_ID, body=json.dumps(body))
result = json.loads(response["body"].read())

text = result["content"][0]["text"]
print(text)
print(json.loads(text))

```

<div class='source-links'>
  <a href='https://github.com/aws-samples/sample-ai-possibilities/blob/main/snippets/structured-output-bedrock/03_invoke_model_anthropic_native.py' class='btn btn-primary'>
    View Raw File
  </a>
</div>
