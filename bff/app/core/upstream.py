def upstream_message(response, fallback):
    try:
        data = response.json()
    except ValueError:
        return fallback
    if not isinstance(data, dict):
        return fallback
    for key in ("errorMessage", "detail"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return fallback
