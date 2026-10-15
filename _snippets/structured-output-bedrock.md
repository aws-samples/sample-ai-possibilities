---
title: "Structured Outputs on Amazon Bedrock"
date: 2026-10-15
description: "This project is for educational purposes and it is not designed for production use. For production use, please implement proper security, scalability, and compliance measures appropriate for your use case."
layout: snippet
difficulty: easy
source_folder: "snippets/structured-output-bedrock"

tags:
  - bedrock
  - structured-outputs
  - python
  - jupyter
  - json-schema
technologies:
  - Python 3.9+
  - AWS SDK (boto3)
  - Amazon Bedrock
  - OpenAI SDK (for the Responses API examples)
  - aws-bedrock-token-generator
---

# Structured Outputs on Amazon Bedrock

Minimal, runnable examples of getting JSON-schema-constrained output from models on Amazon Bedrock, across both Bedrock endpoints and the mechanisms available on each.

## Overview

Anthropic's own [structured outputs documentation](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) states that `output_config` was, at launch, only available on Bedrock through a legacy integration, for a short list of models -- not through Converse at all. That's no longer the full picture: this snippet shows two independent mechanisms that work far more broadly today, plus the OpenAI-compatible Responses API, which supports structured output identically on both `bedrock-runtime` and `bedrock-mantle`.

Each script is a flat, single-purpose example -- no classes, no CLI framework, nothing to configure beyond the constants at the top:

- `01_converse_bedrock_native.py` -- Converse with Bedrock's own schema field (`outputConfig`). Cross-provider: verified against Anthropic, OpenAI, and Moonshot (Kimi) models.
- `02_converse_anthropic_native.py` -- Converse with Anthropic's native `output_config` field, tunneled through `additionalModelRequestFields`. Anthropic-only.
- `03_invoke_model_anthropic_native.py` -- InvokeModel with the same Anthropic-native `output_config` field, this time as a plain body field.
- `04_responses_api.py` -- OpenAI-compatible Responses API. Same code works on either Bedrock endpoint; just swap `BASE_URL` and the model id format.
- `structured_output_on_bedrock.ipynb` -- all four, with explanation and a summary table of what's supported where.

## Tags

- bedrock
- structured-outputs
- python
- jupyter
- json-schema

## Technologies

- Python 3.9+
- AWS SDK (boto3)
- Amazon Bedrock
- OpenAI SDK (for the Responses API examples)
- aws-bedrock-token-generator

## Difficulty

Easy

## Prerequisites

- Python 3.9+
- An AWS account with Bedrock model access, and credentials available via the standard AWS credential chain (`aws configure`, environment variables, etc.)

## Setup

```bash
# Clone the repository
git clone https://github.com/aws-samples/sample-ai-possibilities.git
cd sample-ai-possibilities/snippets/structured-output-bedrock

# Install dependencies
pip install -r requirements.txt

# Run any individual example
python 01_converse_bedrock_native.py

# Or open the notebook
jupyter notebook structured_output_on_bedrock.ipynb
```

### Cleanup Instructions

No resources are created -- these scripts only make inference calls. Nothing to clean up.

## Security

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for security issue notifications.

## Notes

This project is for educational purposes and it is not designed for production use. For production use, please implement proper security, scalability, and compliance measures appropriate for your use case.


<div class='source-links'>
  <h3>View Source</h3>
  <a href='https://github.com/aws-samples/sample-ai-possibilities/tree/main/snippets/structured-output-bedrock' class='btn btn-primary'>
    View on GitHub
  </a>
</div>
