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
    if isinstance(parameters, dict) and "reasoning_effort" in parameters:
        value = parameters["reasoning_effort"]
    elif isinstance(constraints, dict) and "reasoning_effort" in constraints:
        value = constraints["reasoning_effort"]
    elif isinstance(supplier_config, dict) and "reasoning_effort" in supplier_config:
        value = supplier_config["reasoning_effort"]
    else:
        value = "medium"
    if not isinstance(value, str) or value not in REASONING_EFFORTS:
        raise ReasoningEffortError(value)
    return value


def validate_reasoning_definition(*, definition, capability):
    if not isinstance(definition, dict):
        return
    constraints = definition.get("constraints")
    if not isinstance(constraints, dict) or "reasoning_effort" not in constraints:
        return
    value = constraints["reasoning_effort"]
    if (
        capability != "text"
        or not isinstance(value, str)
        or value not in REASONING_EFFORTS
    ):
        raise ReasoningEffortError(value)
