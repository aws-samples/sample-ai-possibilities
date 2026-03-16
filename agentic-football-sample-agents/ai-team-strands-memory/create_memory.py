"""One-time script to create an AgentCore Memory resource for the memory team.

Creates a short-term memory (STM) resource for cross-tick recall.
No long-term strategies are defined — raw events are retained for the
duration of the match session only.

Usage:
    AWS_DEFAULT_REGION=us-east-1 python3 create_memory.py

Prints the MEMORY_ID to stdout. Export it before deploying agents:
    export MEMORY_ID=<printed-id>
"""

import os
from bedrock_agentcore.memory import MemoryClient

region = os.environ.get("AWS_DEFAULT_REGION")
if not region:
    raise RuntimeError("AWS_DEFAULT_REGION environment variable is required")

client = MemoryClient(region_name=region)

memory = client.create_or_get_memory(
    name="AITeamMatchMemory",
    description="Short-term memory for AI soccer team agents — persists game tick history within a match",
)

memory_id = memory.get("id")
print(f"Memory resource ready: {memory_id}")
print(f"Export it:  export MEMORY_ID={memory_id}")
