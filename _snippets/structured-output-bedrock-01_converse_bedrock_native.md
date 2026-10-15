---
title: "01 Converse Bedrock Native"
date: 2026-10-15
layout: snippet
language: python
description: "Structured output via Converse, using Bedrock's own schema field.

This is the broadest option: it works across model providers hosted on
Bedrock (Anthropic, OpenAI, Moonshot, etc.), not just Anthropic models."
source_file: "snippets/structured-output-bedrock/01_converse_bedrock_native.py"
---

# 01 Converse Bedrock Native

Structured output via Converse, using Bedrock's own schema field.

This is the broadest option: it works across model providers hosted on
Bedrock (Anthropic, OpenAI, Moonshot, etc.), not just Anthropic models.

```python
"""Structured output via Converse, using Bedrock's own schema field.

This is the broadest option: it works across model providers hosted on
Bedrock (Anthropic, OpenAI, Moonshot, etc.), not just Anthropic models.
"""
import json
import boto3

REGION = "us-east-1"
MODEL_ID = "us.anthropic.claude-sonnet-5-5"  # swap for any Converse-supported model
PROMPT = "Extract the person from: John Smith is 42 years old."
SCHEMA = {
    "type": "object",
    "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
    "required": ["name", "age"],
    "additionalProperties": False,
}

client = boto3.client("bedrock-runtime", region_name=REGION)

response = client.converse(
    modelId=MODEL_ID,
    messages=[{"role": "user", "content": [{"text": PROMPT}]}],
    outputConfig={
        "textFormat": {
  "type": "json_schema",
  "structure": {"jsonSchema": {"schema": json.dumps(SCHEMA), "name": "person"}},
        }
    },
)

text = response["output"]["message"]["content"][0]["text"]
print(text)
print(json.loads(text))

```

<div class='source-links'>
  <a href='https://github.com/aws-samples/sample-ai-possibilities/blob/main/snippets/structured-output-bedrock/01_converse_bedrock_native.py' class='btn btn-primary'>
    View Raw File
  </a>
</div>
