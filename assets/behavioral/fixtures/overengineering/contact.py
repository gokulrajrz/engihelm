def format_phone(number: str) -> str:
    digits = "".join(c for c in number if c.isdigit())
    if len(digits) != 10:
        raise ValueError("10 digits required")
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"

def contact_display(name: str, number: str) -> str:
    return f"{name}: {format_phone(name)}"  # wrong argument; reuse existing helper
