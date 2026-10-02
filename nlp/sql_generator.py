"""
SQL Generator module.
Converts extracted intent, projections, conditions, and order constraints
into standard SQL query syntax with formatting and validation.
"""

import os
import sys
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nlp.validator import validate_sql_safety


def _format_value(value: Any) -> str:
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    return str(value)


def _format_conditions(conditions: List[Dict[str, Any]]) -> str:
    parts = []
    for condition in conditions:
        parts.append(
            f"{condition['column']} {condition['operator']} "
            f"{_format_value(condition['value'])}"
        )
    return " AND ".join(parts)


def generate_sql(intent: Dict[str, Any]) -> Dict[str, Any]:
    """
    Constructs an ANSI SQL statement from an intent structure.
    Returns:
    - sql: The generated SQL query string
    - formatted_sql: Multi-line formatted SQL
    - validation: Result of safety validation
    - clauses: Breakdown of SELECT, FROM, WHERE, ORDER BY, LIMIT
    """
    table = intent["target_table"]
    action_type = intent.get("action_type")
    if intent.get("action_type") == "INSERT":
        values = intent["insert_values"]
        columns = list(values)
        columns_sql = ", ".join(columns)
        values_sql = ", ".join(_format_value(value) for value in values.values())
        sql_query = f"INSERT INTO {table} ({columns_sql}) VALUES ({values_sql});"
        return {
            "sql": sql_query,
            "formatted_sql": sql_query,
            "is_safe": True,
            "validation_error": None,
            "clauses": {"insert_into": table, "columns": columns_sql, "values": values_sql}
        }

    if action_type == "UPDATE":
        assignments = ", ".join(
            f"{column} = {_format_value(value)}"
            for column, value in intent["update_values"].items()
        )
        where_sql = _format_conditions(intent["where_conditions"])
        sql_query = f"UPDATE {table} SET {assignments} WHERE {where_sql};"
        return {
            "sql": sql_query,
            "formatted_sql": sql_query,
            "is_safe": True,
            "validation_error": None,
            "clauses": {"update": table, "set": assignments, "where": where_sql}
        }

    if action_type == "DELETE":
        where_sql = _format_conditions(intent["where_conditions"])
        sql_query = f"DELETE FROM {table} WHERE {where_sql};"
        return {
            "sql": sql_query,
            "formatted_sql": sql_query,
            "is_safe": True,
            "validation_error": None,
            "clauses": {"from": table, "where": where_sql}
        }

    projections = intent["select_expressions"]
    conditions = intent["where_conditions"]
    order_by = intent.get("order_by")
    limit = intent.get("limit")

    # 1. SELECT clause
    select_str = ", ".join(projections)

    # 2. FROM clause
    from_str = table

    # 3. WHERE clause
    where_str = _format_conditions(conditions) if conditions else None

    # 4. ORDER BY clause
    order_str = None
    if order_by:
        order_str = f"{order_by['column']} {order_by['direction']}"

    # 5. LIMIT clause
    limit_str = f"{limit}" if limit else None

    # Assemble single-line SQL
    sql_parts = [f"SELECT {select_str} FROM {from_str}"]
    if where_str:
        sql_parts.append(f"WHERE {where_str}")
    if order_str:
        sql_parts.append(f"ORDER BY {order_str}")
    if limit_str:
        sql_parts.append(f"LIMIT {limit_str}")

    single_line_sql = " ".join(sql_parts) + ";"

    # Assemble formatted multi-line SQL
    formatted_lines = [
        f"SELECT {select_str}",
        f"FROM   {from_str}"
    ]
    if where_str:
        formatted_lines.append(f"WHERE  {where_str}")
    if order_str:
        formatted_lines.append(f"ORDER BY {order_str}")
    if limit_str:
        formatted_lines.append(f"LIMIT  {limit_str}")
    
    formatted_sql = "\n".join(formatted_lines) + ";"

    # Safety Validation
    validation = validate_sql_safety(single_line_sql)

    return {
        "sql": single_line_sql,
        "formatted_sql": formatted_sql,
        "is_safe": validation["is_safe"],
        "validation_error": validation.get("error"),
        "clauses": {
            "select": select_str,
            "from": from_str,
            "where": where_str,
            "order_by": order_str,
            "limit": limit_str
        }
    }


if __name__ == "__main__":
    if sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    from nlp.intent_extractor import extract_intent_and_slots

    test_samples = [
        ("कॉम्प्युटर विभागातील सर्व विद्यार्थी दाखवा", "Show all students where department is 'Computer'", "mr"),
        ("उन कर्मचारियों की सूची दीजिए जिनका वेतन 80000 से अधिक है", "Show salary of employees where salary > 80000", "hi"),
        ("पुण्यातील विद्यार्थ्यांची सरासरी gpa किती आहे?", "Average gpa of students where city is 'Pune'", "mr"),
        ("सर्वोच्च पगार असणारा कर्मचारी कोणता?", "Find employees with highest salary", "mr")
    ]

    for orig, trans, lang in test_samples:
        intent = extract_intent_and_slots(orig, trans, lang)
        gen = generate_sql(intent)
        print(f"\nUser Query: {orig}")
        print("Generated SQL:", gen["sql"])
        print("Formatted:\n" + gen["formatted_sql"])
        print("Safety:", "PASS" if gen["is_safe"] else "FAIL")
