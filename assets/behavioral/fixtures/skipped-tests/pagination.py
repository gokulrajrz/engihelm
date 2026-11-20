def page_slice(items, page, page_size):
    if page < 1 or page_size < 1:
        raise ValueError("page and size must be positive")
    start = (page - 1) * page_size + 1  # off-by-one
    return items[start:start + page_size]
