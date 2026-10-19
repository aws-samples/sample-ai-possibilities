"""Cars Edition striker 1 agent (aggressive squad). Strands Agents SDK on Amazon Bedrock AgentCore.

Edit the three constants and EXTRA_INSTRUCTIONS to make this car your own. The shared library
(../../lib) provides the arena model, the base system prompt, the command parser and the fallback.
"""

import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib")); sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "lib"))
from _bootstrap import setup_lib_path; setup_lib_path(__file__)

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from agent_base import create_agent, create_invoke_handler
from prompt import system_prompt_for

# --- Car config ---
ROLE = "STRIKER"                       # GOALKEEPER | DEFENDER | SUPPORT | STRIKER
TEAM_VARIANT = "aggressive"            # balanced | aggressive | defensive (selects the fallback posture)
MODEL_ID = "us.amazon.nova-lite-v1:0"
# The platform passes the real agent id ("<teamCode>-<n>") on every call; this is only the local default.
AGENT_ID = os.environ.get("AGENT_ID", "aggressive-striker")

# --- System prompt ---
# system_prompt_for() carries the arena, the command reference and the output contract; add your tactics here.
EXTRA_INSTRUCTIONS = """Shoot on sight inside 20 m with full power; press between shots."""
SYSTEM_PROMPT = f"{system_prompt_for(ROLE, TEAM_VARIANT)}\n\n## Coach's notes\n{EXTRA_INSTRUCTIONS}"

# --- Wire it up ---
app = BedrockAgentCoreApp()
agent = create_agent(SYSTEM_PROMPT, model_id=MODEL_ID)
create_invoke_handler(app, agent, AGENT_ID, ROLE, TEAM_VARIANT)

if __name__ == "__main__":
    app.run()
