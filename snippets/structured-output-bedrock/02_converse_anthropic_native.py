"""Structured output via Converse, using Anthropic's native output_config field.

Anthropic-only: tunnels Anthropic's own `output_config.format` through
Converse's additionalModelRequestFields. Other providers reject or ignore it
-- see 01_converse_bedrock_native.py for the cross-provider equivalent.
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

response = client.converse(
    modelId=MODEL_ID,
    messages=[{"role": "user", "content": [{"text": PROMPT}]}],
    additionalModelRequestFields={
        "output_config": {"format": {"type": "json_schema", "schema": SCHEMA}}
    },
)

text = response["output"]["message"]["content"][0]["text"]
print(text)
print(json.loads(text))
