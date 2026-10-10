# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

import os

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
os.environ.setdefault("OPENHANDS_SUPPRESS_BANNER", "1")

from openhands.sdk import LLM, Agent, Conversation, Tool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.terminal import TerminalTool
from pydantic import SecretStr


TASK = """
Inspect /work and reproduce the group-booking failure using the supplied tests.
Fix remaining() so confirmed bookings consume their seats, not one place each.
Preserve cancellation handling, input validation, and negative overbooking results.
Only capacity.py may change. Do not change tests, add files, or install dependencies.
Run python -B -m unittest -v before and after the repair.
Explain the cause, changed behavior, and any unresolved issue in your final response.
If the task requires a broader change, stop and explain instead of expanding scope.
"""


def build_agent():
    llm = LLM(model=os.environ["AIC_CODING_MODEL"],
              base_url=os.environ["AIC_CODING_BASE_URL"],
              api_key=SecretStr(os.environ["AIC_CODING_TOKEN"]),
              timeout=30, stream_idle_timeout=30, num_retries=0, max_output_tokens=1536)
    return Agent(llm=llm, tools=[Tool(name=TerminalTool.name),
                               Tool(name=FileEditorTool.name)])


def run():
    agent = build_agent()
    conversation = Conversation(
        agent=agent, workspace="/work", max_iteration_per_run=12,
        persistence_dir="/tmp/conversation",
        callbacks=[lambda event: print(event.model_dump_json(), flush=True)],
    )
    try:
        conversation.send_message(TASK)
        conversation.run()
    finally:
        conversation.close()


if __name__ == "__main__":
    run()
