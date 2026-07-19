IMAGE_SIZES = frozenset({"auto", "1024x1024", "1024x1536", "1536x1024"})
IMAGE_QUALITIES = frozenset({"auto", "low", "medium", "high"})


class ImageOptionError(RuntimeError):
    def __init__(self, code, value):
        super().__init__(code)
        self.code = code
        self.value = value


def resolve_image_options(*, request, model_definition, supplier_config):
    request = request if isinstance(request, dict) else {}
    definition = model_definition if isinstance(model_definition, dict) else {}
    config = supplier_config if isinstance(supplier_config, dict) else {}
    constraints = definition.get("constraints")
    constraints = constraints if isinstance(constraints, dict) else {}

    size = _first_present(
        request, "size",
        config, "image_size",
        definition, "default_size",
        fallback="1024x1024",
    )
    quality = _first_present(
        request, "quality",
        config, "image_quality",
        constraints, "default_quality",
        fallback="auto",
    )
    _validate_size(size, constraints.get("supported_sizes"))
    _validate_quality(quality, constraints.get("supported_qualities"))
    return {"size": size, "quality": quality}


def _first_present(*parts, fallback):
    for mapping, key in zip(parts[0::2], parts[1::2]):
        if isinstance(mapping, dict) and key in mapping:
            value = mapping[key]
            if isinstance(value, str) and value:
                return value
            return value
    return fallback


def _validate_size(value, declared):
    if not isinstance(value, str) or not value:
        raise ImageOptionError("INVALID_IMAGE_SIZE", value)
    if declared is None:
        return
    allowed = _declared_values(declared, IMAGE_SIZES, "INVALID_IMAGE_SIZE")
    if value not in allowed:
        raise ImageOptionError("INVALID_IMAGE_SIZE", value)


def _validate_quality(value, declared):
    if not isinstance(value, str) or value not in IMAGE_QUALITIES:
        raise ImageOptionError("INVALID_IMAGE_QUALITY", value)
    if declared is None:
        return
    allowed = _declared_values(declared, IMAGE_QUALITIES, "INVALID_IMAGE_QUALITY")
    if value not in allowed:
        raise ImageOptionError("INVALID_IMAGE_QUALITY", value)


def _declared_values(value, safe_values, code):
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or item not in safe_values for item in value)
    ):
        raise ImageOptionError(code, value)
    return tuple(dict.fromkeys(value))
