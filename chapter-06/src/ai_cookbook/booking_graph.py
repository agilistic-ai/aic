from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from .booking_action import commit, fingerprint
from .booking_verify import verify


class Job(TypedDict, total=False):
    request_id: str
    actor: str
    proposal: dict
    question: str
    trace: list
    model_configuration: dict
    approval_token: str
    receipt: dict
    confirmation: dict


def build_graph(store, checkpointer):
    def await_approval(state):
        store.require_member(state["actor"])
        token = interrupt({
            "request_id": state["request_id"], "proposal": state["proposal"],
            "fingerprint": fingerprint(state["actor"], state["request_id"], state["proposal"]),
        })
        if not isinstance(token, str) or not token:
            raise ValueError("Resume requires an application-issued approval token.")
        return {"approval_token": token}

    def perform(state):
        receipt = commit(store, state["actor"], state["request_id"],
                         state["proposal"], state["approval_token"])
        return {"receipt": receipt}

    def confirm(state):
        return {"confirmation": verify(store, state["actor"], state["request_id"],
                                       state["proposal"])}

    builder = StateGraph(Job)
    builder.add_node("approval", await_approval)
    builder.add_node("perform", perform)
    builder.add_node("confirm", confirm)
    builder.add_edge(START, "approval")
    builder.add_edge("approval", "perform")
    builder.add_edge("perform", "confirm")
    builder.add_edge("confirm", END)
    return builder.compile(checkpointer=checkpointer)
