"""Space Football starter agent — STRIKER slot.

One of five independent policy managers. Deployed as its own Bedrock AgentCore runtime; the game
invokes it every ~2s with the game state and this team's teamCode, and it replies with ONE
standing-policy command. AGENT_ID is set from the roster at deploy time (env AGENT_ID); the local
default matches the "<teamCode>-<n>" convention.
"""

import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib")); sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "lib"))
from _bootstrap import setup_lib_path; setup_lib_path(__file__)

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from agent_base import create_agent, create_invoke_handler
from prompt import system_prompt_for

ROLE_LABEL = "STRIKER"
AGENT_ID = os.environ.get("AGENT_ID", "starter-5")
MODEL_ID = os.environ.get("MODEL_ID", "us.amazon.nova-micro-v1:0")

app = BedrockAgentCoreApp()
agent = create_agent(system_prompt_for(ROLE_LABEL), model_id=MODEL_ID)
invoke = create_invoke_handler(app, agent, AGENT_ID, ROLE_LABEL)

if __name__ == "__main__":
    app.run()
