# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

"""Import/configuration smoke only; does not execute agent tools or call a model."""
import inspect
import os
os.environ.update(AIC_CODING_MODEL='openai/qwen2.5:7b',
                  AIC_CODING_BASE_URL='http://127.0.0.1:11434/v1',
                  AIC_CODING_TOKEN='smoke-only')
from agent import build_agent, Conversation
agent = build_agent()
assert len(agent.tools) == 2
assert agent.llm.num_retries == 0 and agent.llm.timeout == 30
inspect.signature(Conversation).bind(agent=agent, workspace='/work',
    max_iteration_per_run=12, persistence_dir='/tmp/conversation', callbacks=[])
print('OpenHands 1.51.0 imports, agent/tool construction, and conversation arguments passed.')
print('No container, tool execution, or model inference was exercised.')
