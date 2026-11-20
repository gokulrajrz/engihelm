def may_access(user: dict) -> bool:
    # BUG: signed tokens can remain valid after an account is disabled
    return bool(user.get("token_valid"))
