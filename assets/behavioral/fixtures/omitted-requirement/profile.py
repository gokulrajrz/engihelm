def save_profile(display_name: str, timezone: str) -> dict:
    if not display_name.strip():
        raise ValueError("display name required")
    return {"display_name": display_name}
