"""Structured output via the OpenAI-compatible Responses API on Bedrock.

Works the same way on both Bedrock endpoints -- just swap BASE_URL:
  bedrock-runtime.{region}.amazonaws.com/openai/v1   (needs a cross-region
                                                       profile model id, e.g. "us.openai...")
  bedrock-mantle.{region}.api.aws/openai/v1          (plain model id, e.g. "openai...")

Auth is a short-lived bearer token derived from your AWS credentials --
no SigV4 request signing needed.
"""
from aws_bedrock_token_generator import provide_token
from openai import OpenAI

REGION = "us-east-1"
BASE_URL = f"https://bedrock-mantle.{REGION}.api.aws/openai/v1"
MODEL_ID = "openai.gpt-5.6-sol"
# For bedrock-runtime instead, use:
# BASE_URL = f"https://bedrock-runtime.{REGION}.amazonaws.com/openai/v1"
# MODEL_ID = "us.openai.gpt-5.6-sol"

PROMPT = "Extract the person from: John Smith is 42 years old."
SCHEMA = {
    "type": "object",
    "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
    "required": ["name", "age"],
    "additionalProperties": False,
}

token = provide_token(REGION)
client = OpenAI(base_url=BASE_URL, api_key=token)

response = client.responses.create(
    model=MODEL_ID,
    input=PROMPT,
    text={"format": {"type": "json_schema", "name": "person", "schema": SCHEMA, "strict": True}},
)

print(response.output_text)
