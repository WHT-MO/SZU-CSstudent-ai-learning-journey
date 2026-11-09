def can_retry(attempts_used: int, max_attempts: int) -> bool:
    """低于上限时返回 True，达到上限时返回 False。"""
    return attempts_used <= max_attempts