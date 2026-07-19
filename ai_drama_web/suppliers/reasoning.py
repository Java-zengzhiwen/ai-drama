REASONING_EFFORTS = frozenset({"none", "low", "medium", "high", "xhigh", "max"})
LEGACY_REASONING_EFFORTS = ("low", "medium", "high")


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
    elif isinstance(supplier_config, dict) and "reasoning_effort" in supplier_config:
        value = supplier_config["reasoning_effort"]
    elif isinstance(constraints, dict) and "reasoning_effort" in constraints:
        value = constraints["reasoning_effort"]
    else:
        value = "medium"
    if not isinstance(value, str) or value not in supported_reasoning_efforts(model_definition):
        raise ReasoningEffortError(value)
    return value


def supported_reasoning_efforts(model_definition):
    constraints = (
        model_definition.get("constraints")
        if isinstance(model_definition, dict)
        else {}
    )
    declared = constraints.get("supported_reasoning_efforts") if isinstance(constraints, dict) else None
    if not isinstance(declared, list) or not declared:
        return LEGACY_REASONING_EFFORTS
    if any(not isinstance(value, str) or value not in REASONING_EFFORTS for value in declared):
        raise ReasoningEffortError(declared)
    return tuple(dict.fromkeys(declared))


def validate_reasoning_definition(*, definition, capability):
    if not isinstance(definition, dict):
        return
    constraints = definition.get("constraints")
    if not isinstance(constraints, dict):
        return
    if "reasoning_effort" not in constraints and "supported_reasoning_efforts" not in constraints:
        return
    if capability != "text":
        raise ReasoningEffortError(constraints.get("reasoning_effort"))
    supported = supported_reasoning_efforts(definition)
    value = constraints.get("reasoning_effort", "medium")
    if not isinstance(value, str) or value not in supported:
        raise ReasoningEffortError(value)
