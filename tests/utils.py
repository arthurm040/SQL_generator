def _normalize_sql(sql: str) -> str:
    """Remove extra whitespace and newlines for consistent testing"""
    return " ".join(sql.split())
