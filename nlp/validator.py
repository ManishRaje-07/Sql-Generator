"""
SQL Safety Validator module.
Ensures generated SELECT statements contain no destructive keywords or stacked queries.
Generated SQL is returned as text and is never executed by this application.
"""

import re
from typing import Dict, Any, List
# Dangerous SQL keywords that modify schema or data
FORBIDDEN_KEYWORDS = [
    r'\bDROP\b', r'\bDELETE\b', r'\bUPDATE\b', r'\bINSERT\b',
    r'\bALTER\b', r'\bTRUNCATE\b', r'\bCREATE\b', r'\bREPLACE\b',
    r'\bEXEC\b', r'\bEXECUTE\b', r'\bATTACH\b', r'\bDETACH\b',
    r'\bPRAGMA\b', r'\bGRANT\b', r'\bREVOKE\b', r'\bVACUUM\b'
]


def validate_sql_safety(sql: str) -> Dict[str, Any]:
    """
    Validates a SQL query for execution safety:
    1. Must begin with SELECT
    2. Must not contain destructive statements
    3. Must not chain multiple queries (no semicolons in query body)
    4. Must contain only one statement
    """
    cleaned = sql.strip()

    # 1. Empty check
    if not cleaned:
        return {
            "is_safe": False,
            "error": "SQL query is empty."
        }

    # 2. Must start with SELECT
    if not re.match(r'^\s*SELECT\b', cleaned, re.IGNORECASE):
        return {
            "is_safe": False,
            "error": "Only SELECT read-only queries are permitted for safety."
        }

    # 3. Check for multiple queries (semicolon inside query)
    statements = [s for s in cleaned.split(';') if s.strip()]
    if len(statements) > 1:
        return {
            "is_safe": False,
            "error": "Multiple queries in a single execution are forbidden (SQL injection defense)."
        }

    # 4. Check forbidden keywords
    upper_sql = cleaned.upper()
    for pattern in FORBIDDEN_KEYWORDS:
        if re.search(pattern, upper_sql):
            matched = re.search(pattern, upper_sql).group(0)
            return {
                "is_safe": False,
                "error": f"Disallowed SQL keyword detected: '{matched}'. Only read-only operations are supported."
            }

    return {
        "is_safe": True,
        "error": None
    }


if __name__ == "__main__":
    tests = [
        "SELECT * FROM students WHERE department = 'Computer';",
        "DROP TABLE students;",
        "SELECT * FROM students; DELETE FROM students;",
        "SELECT * FROM passwords;",
        "UPDATE employees SET salary = 999999;"
    ]
    for q in tests:
        val = validate_sql_safety(q)
        status = "SAFE" if val["is_safe"] else f"BLOCKED: {val['error']}"
        print(f"[{status}] -> {q}")
