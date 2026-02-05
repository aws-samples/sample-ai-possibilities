---
title: "Getting Started with Amazon S3 Vectors and Bedrock Embeddings"
date: 2026-02-05
description: "This library is licensed under the MIT-0 License. See the [LICENSE](../../LICENSE) file."
layout: snippet
difficulty: easy
source_folder: "snippets/s3-vector-search"

tags:
  - bedrock
  - s3-vectors
  - jupyter
  - embeddings
  - python
  - vector-search
technologies:
  - Python
  - AWS SDK (Boto3)
  - Amazon S3 Vectors
  - Amazon Bedrock (Cohere model)
  - Jupyter Notebooks
---

# Getting Started with Amazon S3 Vectors and Bedrock Embeddings

A Jupyter notebook demo that shows how to create a vector index using Amazon S3 Vectors and populate it with Cohere embeddings generated through Amazon Bedrock. It then performs similarity queries and explores metadata-based filtering.

## Overview

This notebook demonstrates how to use Amazon S3 Vectors — a new capability in S3 that supports native vector storage and similarity search — in combination with Amazon Bedrock’s Cohere embedding models. You'll learn how to:

- Create a vector bucket and index
- Generate embeddings from text using Cohere via Bedrock
- Store vectors with metadata using `put_vectors`
- Query the index using `query_vectors` with optional filters
- Inspect stored vector keys using `list_keys`

This is useful for developers and ML practitioners building search, recommendation, or semantic retrieval systems without the need to manage infrastructure. It leverages fully managed AWS services and shows best practices for key management, filtering, and performance timing.

## Tags

- bedrock
- s3-vectors
- jupyter
- embeddings
- python
- vector-search

## Technologies

- Python
- AWS SDK (Boto3)
- Amazon S3 Vectors
- Amazon Bedrock (Cohere model)
- Jupyter Notebooks

## Difficulty

Easy

## Prerequisites

- Python 3.11+
- Jupyter Notebook or VS Code with Jupyter support
- AWS Account with access to:
  - Amazon Bedrock (with Cohere embed model access)
  - Amazon S3 Vectors (preview or GA access)
  - Permissions for `bedrock:InvokeModel`, `s3vectors:*` (granular permissions are always recommended)

## Setup

```bash
# Clone the repository
git clone https://github.com/aws-samples/sample-ai-possibilities.git
cd sample-ai-possibilities/snippets/s3-vectors-search

# (Optional) Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # or .venv\\Scripts\\activate on Windows

# Install dependencies
pip install boto3 notebook
```

## Security

See [CONTRIBUTING](../../CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](../../LICENSE) file.

<div class='source-links'>
  <h3>View Source</h3>
  <a href='https://github.com/aws-samples/sample-ai-possibilities/tree/main/snippets/s3-vector-search' class='btn btn-primary'>
    View on GitHub
  </a>
</div>
