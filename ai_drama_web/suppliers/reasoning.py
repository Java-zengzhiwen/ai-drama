REASONING_EFFORTS = frozenset({"low", "medium", "high"})


class ReasoningEffortError(RuntimeError):
    code = "INVALID_REASONING_EFFORT"

    def __init__(self, value):
        super().__init__(self.code)
        self.value = value


def resolve_reasoning_effort(*, request, model_definition, supplier_config):
    parameters = request.get("parameters") if isinstance(request, dict) else {}
    constraints = (
        model_definition.get("constraints")
        if isinstance(model_definition, dict)
        else {}
    )
    value = (
        (parameters or {}).get("reasoning_effort")
        or (constraints or {}).get("reasoning_effort")
        or (supplier_config or {}).get("reasoning_effort")
        or "medium"
    )
    if value not in REASONING_EFFORTS:
        raise ReasoningEffortError(value)
    return value
