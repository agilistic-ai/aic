from .booking_action import Proposal


def verify(store, actor, request_id, proposal):
    proposal = Proposal.model_validate(proposal).model_dump()
    receipt = store.lookup(request_id, actor)
    expected = {"request_id": request_id, "actor": actor,
                "slot_id": proposal["slot_id"], "start_utc": proposal["start_utc"],
                "slot_version": proposal["version"], "status": "confirmed"}
    if receipt is None or any(receipt.get(key) != value for key, value in expected.items()):
        raise RuntimeError("Booking outcome hasn't been verified.")
    return receipt
