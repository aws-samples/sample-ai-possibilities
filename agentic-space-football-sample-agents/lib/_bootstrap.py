"""Bootstrap helper — sets up sys.path so shared lib is importable.

Usage (at the very top of each agent's main.py):

    import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib")); sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "lib")); from _bootstrap import setup_lib_path; setup_lib_path(__file__)

Or more readably as two lines:
    import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib")); sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "lib"))
    from _bootstrap import setup_lib_path; setup_lib_path(__file__)
"""

import os
import sys


def setup_lib_path(caller_file: str) -> None:
    """Add the correct lib/ directory to sys.path.

    Works for both layouts:
      - Deployed (AgentCore): agent/lib/ sits next to agent/src/
      - Local dev: agents/lib/ is three levels up from agent/src/main.py
    """
    here = os.path.dirname(os.path.abspath(caller_file))
    lib_deployed = os.path.join(here, "..", "lib")              # agent/lib  (AgentCore)
    lib_local = os.path.join(here, "..", "..", "..", "lib")     # agents/lib (local dev)

    lib_dir = lib_deployed if os.path.isdir(lib_deployed) else lib_local

    # Avoid duplicates
    lib_dir = os.path.normpath(lib_dir)
    if lib_dir not in sys.path:
        sys.path.insert(0, lib_dir)
