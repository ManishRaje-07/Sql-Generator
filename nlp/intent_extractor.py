"""
Intent and Entity Extractor module.
Maps natural language concepts to structured SQL intents:
Target Table, Projected Columns, Aggregations, Where Conditions, Order By, and Limits.
"""

import os
import sys
import re
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nlp.normalizer import (
    normalize_text,
    extract_matched_entities,
    TABLE_SYNONYMS,
    COLUMN_SYNONYMS,
    DEPARTMENT_VALUES,
    CITY_VALUES,
    ROLE_VALUES
)


def _contains_phrase(text: str, phrase: str) -> bool:
    if phrase.isascii() and phrase.isalpha():
        return re.search(rf"\b{re.escape(phrase)}\b", text, re.IGNORECASE) is not None
    return phrase in text


def extract_intent_and_slots(
    original_query: str,
    translated_query: str,
    lang_code: str
) -> Dict[str, Any]:
    """
    Extracts structured SQL semantics:
    - target_table: 'students' | 'employees' | 'departments'
    - action_type: 'SELECT_ALL' | 'SELECT_COLUMNS' | 'AGGREGATE' | 'TOP_N'
    - select_expressions: List of columns or expressions
    - where_conditions: List of {column, operator, value, value_type}
    - order_by: {column, direction} or None
    - limit: int or None
    - reasoning: List of explanation sentences
    """
    combined_text = f"{original_query} {translated_query}".lower()
    norm_original = normalize_text(original_query).lower()
    norm_translated = normalize_text(translated_query).lower()
    insert_verbs = [
        "add", "insert", "register", "जोडा", "जोडा", "जोड़ें", "जोड़ो",
        "दर्ज करें", "दर्ज करा", "नोंदवा", "नोंद करा", "समाविष्ट करा"
    ]
    is_insert_request = any(
        _contains_phrase(text, verb)
        for text in (norm_original, norm_translated)
        for verb in insert_verbs
    )
    update_verbs = ["change", "update", "set", "modify", "बदलें", "बदलो", "बदला", "अपडेट करें", "अपडेट करा", "सुधारें", "कर दें", "कर दो"]
    delete_verbs = ["delete", "remove", "हटाएं", "हटाओ", "मिटाओ", "डिलीट करें", "काढा", "हटवा", "काढून टाका"]
    is_update_request = any(
        _contains_phrase(text, verb)
        for text in (norm_original, norm_translated)
        for verb in update_verbs
    )
    is_delete_request = any(
        _contains_phrase(text, verb)
        for text in (norm_original, norm_translated)
        for verb in delete_verbs
    )
    is_row_mutation = is_insert_request or is_update_request or is_delete_request

    # ── DDL / unsupported intent detection ────────────────────────────────
    # Catch queries that are asking to CREATE/DELETE/MAKE a database or table.
    # These cannot be converted to SELECT queries.
    DDL_KEYWORDS_EN = ["create", "drop", "delete", "insert", "update", "alter", "truncate", "make", "build"]
    DDL_KEYWORDS_MR = ["तयार करा", "बनवा", "काढा", "हटवा", "मिटवा", "नष्ट करा", "बदला", "अपडेट करा"]
    DDL_KEYWORDS_HI = ["बनाओ", "बनाइए", "हटाओ", "मिटाओ", "डिलीट करो", "बदलो", "अपडेट करो", "तैयार करो"]
    DB_WORDS = ["database", "table", "schema", "डेटाबेस", "टेबल", "स्कीमा"]

    is_ddl = False
    for kw in DDL_KEYWORDS_EN + DDL_KEYWORDS_MR + DDL_KEYWORDS_HI:
        if kw in norm_original or kw in norm_translated:
            for dw in DB_WORDS:
                if dw in norm_original or dw in norm_translated:
                    is_ddl = True
                    break
        if is_ddl:
            break

    if is_ddl and not is_row_mutation:
        raise ValueError(
            "This request could not be converted into supported SQL. "
            "Try asking for a SELECT query or a database creation statement."
        )
    # ── End DDL check ──────────────────────────────────────────────────────

    # Extract entities from both original and translated text
    ent_orig = extract_matched_entities(norm_original)
    ent_trans = extract_matched_entities(norm_translated)

    # Merge entities
    entities = {
        "tables": list(set(ent_orig["tables"] + ent_trans["tables"])),
        "columns": list(set(ent_orig["columns"] + ent_trans["columns"])),
        "departments": list(set(ent_orig["departments"] + ent_trans["departments"])),
        "cities": list(set(ent_orig["cities"] + ent_trans["cities"])),
        "roles": list(set(ent_orig["roles"] + ent_trans["roles"])),
        "aggregations": list(set(ent_orig["aggregations"] + ent_trans["aggregations"])),
        "operators": ent_orig["operators"] if ent_orig["operators"] else ent_trans["operators"],
        "numbers": ent_orig["numbers"] if ent_orig["numbers"] else ent_trans["numbers"]
    }

    reasoning = []

    # 1. Determine Target Table
    # Priority rules:
    # - If query specifically refers to students/विद्यार्थी/छात्र -> 'students'
    # - If query specifically refers to employees/कर्मचारी/staff -> 'employees'
    # - If query asks about faculty/departments/HOD/budget -> 'departments' (or 'employees' if employee salary/experience)
    target_table = "students"

    has_students = any(syn in norm_original or syn in norm_translated for syn in TABLE_SYNONYMS["students"])
    has_employees = any(syn in norm_original or syn in norm_translated for syn in TABLE_SYNONYMS["employees"])
    has_departments = any(syn in norm_original or syn in norm_translated for syn in [
        "विभागांची माहिती", "सर्व विभाग", "विभाग यादी", "विभाग प्रमुख", "hod", "head of department",
        "faculty count", "teachers count", "departments", "department list", "budget"
    ])

    if has_students:
        target_table = "students"
        reasoning.append("Identified target table as 'students' based on student entity keywords.")
    elif has_employees:
        target_table = "employees"
        reasoning.append("Identified target table as 'employees' based on employee/staff entity keywords.")
    elif "salary" in entities["columns"] or "experience_years" in entities["columns"] or entities["roles"]:
        target_table = "employees"
        reasoning.append("Identified target table as 'employees' based on salary/role/experience attributes.")
    elif "budget" in entities["columns"] or "faculty_count" in entities["columns"] or "hod_name" in entities["columns"] or has_departments:
        target_table = "departments"
        reasoning.append("Identified target table as 'departments' based on department/budget/faculty attributes.")
    elif "gpa" in entities["columns"] or "year_of_study" in entities["columns"]:
        target_table = "students"
        reasoning.append("Identified target table as 'students' based on academic attributes (GPA/year).")
    else:
        target_table = "students"
        reasoning.append("Defaulted to 'students' table as primary academic entity.")

    if is_update_request:
        source_text = normalize_text(original_query)
        update_column = next(iter(ent_orig["columns"]), None)
        if update_column is None:
            update_column = next(iter(ent_trans["columns"]), None)
        if update_column is None:
            field_match = re.search(
                r"['’]s\s+([A-Za-z_][A-Za-z0-9_]*)\s+(?:to|=)",
                source_text,
                re.IGNORECASE
            )
            update_column = field_match.group(1) if field_match else None
        if update_column is None:
            raise ValueError("To update a record, specify the field and its new value.")

        value_match = re.search(
            r"(?:\bto\b|=|करें|करो|कर\s+दें|कर\s+दो|रखें|रखे)\s*(['\"])(.*?)\1\s*[.!?]*$"
            r"|(?:\bto\b|=|करें|करो|कर\s+दें|कर\s+दो|रखें|रखे)\s*([-+]?[0-9]+(?:\.[0-9]+)?)\s*[.!?]*$"
            r"|(?:\bto\b|=|करें|करो|कर\s+दें|कर\s+दो|रखें|रखे)\s*([A-Za-z\u0900-\u097F][A-Za-z\u0900-\u097F'-]*)\s*[.!?]*$",
            source_text,
            re.IGNORECASE
        )
        trailing_value_match = None
        if not value_match:
            trailing_value_match = re.search(
                r"([-+]?[0-9]+(?:\.[0-9]+)?)\s+(?:कर\s+दें|कर\s+दो|करें|करो|रखें|रखे)\s*[.!?]*$",
                source_text,
                re.IGNORECASE
            )
        if not value_match and not trailing_value_match:
            raise ValueError("To update a record, include the new field value.")
        if trailing_value_match:
            raw_value = trailing_value_match.group(1)
            update_value = float(raw_value) if "." in raw_value else int(raw_value)
        elif value_match.group(1):
            update_value = value_match.group(2)
        elif value_match.group(3):
            raw_value = value_match.group(3)
            update_value = float(raw_value) if "." in raw_value else int(raw_value)
        else:
            update_value = value_match.group(4)

        where_conditions = []
        id_match = re.search(
            r"(?:\bid\b|identifier|आयडी|आईडी|क्रमांक)\s*(?:is|of|=|है)?\s*([0-9]+)"
            r"|([0-9]+)\s*(?:\bid\b|identifier|आयडी|आईडी|क्रमांक)",
            source_text,
            re.IGNORECASE
        )
        if id_match:
            where_conditions.append({"column": "id", "operator": "=", "value": int(id_match.group(1) or id_match.group(2)), "value_type": "number"})
        else:
            name_match = re.search(r"\b([A-Za-z][A-Za-z'-]*)['’]s\s+", source_text, re.IGNORECASE)
            if not name_match:
                name_match = re.search(r"([A-Za-z\u0900-\u097F]+)\s+(?:की|का|के)\s+", source_text)
            if not name_match:
                name_match = re.search(r"([\u0900-\u097F]+)(?:चे|ची|चा)\s+", source_text)
            generic_subjects = {"the", "student", "students", "employee", "employees", "record", "person", "छात्र", "छात्रों", "विद्यार्थी", "कर्मचारी"}
            if name_match and name_match.group(1).casefold() not in generic_subjects:
                where_conditions.append({"column": "name", "operator": "=", "value": name_match.group(1), "value_type": "string"})

        if not where_conditions:
            raise ValueError("To update a record safely, specify which row to update by name or ID.")

        reasoning.append(f"Recognized an UPDATE request for the '{target_table}' table.")
        return {
            "target_table": target_table,
            "action_type": "UPDATE",
            "select_expressions": [],
            "where_conditions": where_conditions,
            "update_values": {update_column: update_value},
            "order_by": None,
            "limit": None,
            "extracted_entities": entities,
            "reasoning": reasoning
        }

    if is_delete_request:
        source_text = normalize_text(original_query)
        id_match = re.search(
            r"(?:\bid\b|identifier|आयडी|आईडी|क्रमांक)\s*(?:is|of|=|है)?\s*([0-9]+)"
            r"|([0-9]+)\s*(?:\bid\b|identifier|आयडी|आईडी|क्रमांक)",
            source_text,
            re.IGNORECASE
        )
        where_conditions = []
        if id_match:
            where_conditions.append({"column": "id", "operator": "=", "value": int(id_match.group(1) or id_match.group(2)), "value_type": "number"})
        else:
            name_match = re.search(r"\bnamed\s+([A-Za-z][A-Za-z'-]*)", source_text, re.IGNORECASE)
            if name_match:
                where_conditions.append({"column": "name", "operator": "=", "value": name_match.group(1), "value_type": "string"})
            else:
                delete_column = next(
                    (column for column in ["age", "salary", "gpa", "experience_years", "year_of_study", "budget"] if column in ent_orig["columns"]),
                    None
                )
                delete_number = re.search(r"\b([-+]?[0-9]+(?:\.[0-9]+)?)\b", source_text)
                if delete_column and delete_number and ent_orig["operators"]:
                    raw_value = delete_number.group(1)
                    value = float(raw_value) if "." in raw_value else int(raw_value)
                    where_conditions.append({
                        "column": delete_column,
                        "operator": ent_orig["operators"][0],
                        "value": value,
                        "value_type": "number"
                    })
        if not where_conditions:
            raise ValueError("To delete a record safely, specify the row's ID or name.")

        reasoning.append(f"Recognized a DELETE request for the '{target_table}' table with a row filter.")
        return {
            "target_table": target_table,
            "action_type": "DELETE",
            "select_expressions": [],
            "where_conditions": where_conditions,
            "order_by": None,
            "limit": None,
            "extracted_entities": entities,
            "reasoning": reasoning
        }

    if is_insert_request:
        source_text = normalize_text(original_query)
        insert_values = {}

        name_match = re.search(
            r"\bnamed\s+(.+?)(?=\s+(?:with\s+)?(?:id|age)\b|[,;.]|$)",
            source_text,
            re.IGNORECASE
        )
        if not name_match:
            name_match = re.search(
                r"([A-Za-z\u0900-\u097F][A-Za-z\u0900-\u097F'-]*)\s+(?:नावाचा|नावाची|नावाचे|नाम\s+(?:का|की|के))",
                source_text
            )
        if name_match:
            insert_values["name"] = name_match.group(1).strip()

        id_match = re.search(
            r"(?:\bid\b|identifier|आयडी|आईडी|क्रमांक)\s*(?:is|of|=|है)?\s*([0-9]+)"
            r"|([0-9]+)\s*(?:\bid\b|identifier|आयडी|आईडी|क्रमांक)",
            source_text,
            re.IGNORECASE
        )
        if id_match:
            insert_values["id"] = int(id_match.group(1) or id_match.group(2))

        age_match = re.search(
            r"(?:\bage\b|वय|उम्र)\s*(?:is|of|=|है)?\s*([0-9]+)",
            source_text,
            re.IGNORECASE
        )
        if age_match:
            insert_values["age"] = int(age_match.group(1))

        if not insert_values:
            raise ValueError("To add a record, include at least one field value such as a name, ID, or age.")

        reasoning.append(f"Recognized an INSERT request for the '{target_table}' table.")
        return {
            "target_table": target_table,
            "action_type": "INSERT",
            "select_expressions": [],
            "where_conditions": [],
            "order_by": None,
            "limit": None,
            "insert_values": insert_values,
            "extracted_entities": entities,
            "reasoning": reasoning
        }

    # 2. Determine Action / Aggregation / Ordering
    action_type = "SELECT_ALL"
    order_by = None
    limit = None
    select_expressions = ["*"]

    # Check for Aggregations
    # Priority: AVG > SUM > MAX > MIN > COUNT
    has_avg = "AVG" in entities["aggregations"] or any(w in combined_text for w in ["average", "avg", "सरासरी", "औसत"])
    is_total_count = any(w in combined_text for w in ["total number", "total count", "कुल संख्या", "एकूण संख्या"])
    has_sum = not is_total_count and (
        "SUM" in entities["aggregations"]
        or any(w in combined_text for w in ["sum", "total", "एकूण बेरीज", "एकूण", "कुल जोड़", "कुल योग"])
    )
    has_max = "MAX" in entities["aggregations"] or any(w in combined_text for w in ["highest", "maximum", "max", "top", "सर्वोच्च", "सर्वाधिक", "कमाल", "सबसे ज्यादा", "सबसे अधिक", "अधिकतम"])
    has_min = "MIN" in entities["aggregations"] or any(w in combined_text for w in ["lowest", "minimum", "min", "सर्वात कमी", "किमान", "कमीत कमी", "सबसे कम", "न्यूनतम"])
    has_count = is_total_count or "COUNT" in entities["aggregations"] or any(w in combined_text for w in ["count", "how many", "number of", "संख्या", "गिनती"])
    top_n_match = next((
        match for pattern in (
            r"\btop\s+(\d+)\b",
            r"(?:शीर्ष|टॉप)\s+(\d+)",
            r"(?:सर्वात\s+वरचे|वरचे)\s+(\d+)"
        )
        if (match := re.search(pattern, norm_original, re.IGNORECASE))
    ), None)

    measure_columns = ("age", "salary", "gpa", "experience_years", "year_of_study", "budget")
    aggregate_column = next((column for column in measure_columns if column in ent_orig["columns"]), None)
    if aggregate_column is None:
        aggregate_column = next((column for column in measure_columns if column in ent_trans["columns"]), None)
    default_aggregate_column = {
        "employees": "salary",
        "departments": "budget",
        "students": "gpa"
    }[target_table]
    aggregate_column = aggregate_column or default_aggregate_column

    if top_n_match:
        sort_col = next(
            (column for column in measure_columns if column in ent_orig["columns"]),
            default_aggregate_column
        )
        action_type = "TOP_N"
        select_expressions = ["*"]
        order_by = {"column": sort_col, "direction": "DESC"}
        limit = int(top_n_match.group(1))
        reasoning.append(f"Recognized TOP {limit}, ordered by '{sort_col}' DESC.")

    # Check if asking for Top record (e.g. "who has highest salary" -> order by salary desc limit 1)
    is_superlative_record = False
    if not top_n_match and (has_max or has_min):
        # If asking for a person/record ("कोण", "कौन", "who", "which employee", "which student", "find employee")
        if any(w in norm_original for w in ["कोण", "कोणाचा", "कोणता", "कौन", "किसका", "who", "which", "find"]):
            is_superlative_record = True

    if top_n_match:
        pass
    elif is_superlative_record:
        action_type = "TOP_N"
        sort_col = aggregate_column
        direction = "DESC" if has_max else "ASC"
        order_by = {"column": sort_col, "direction": direction}
        limit = 1
        select_expressions = ["*"]
        reasoning.append(f"Identified superlative query: sorting by '{sort_col}' {direction} with LIMIT 1.")
    elif has_avg:
        action_type = "AGGREGATE"
        agg_col = aggregate_column
        select_expressions = [f"ROUND(AVG({agg_col}), 2) AS average_{agg_col}"]
        reasoning.append(f"Identified aggregation: AVG on column '{agg_col}'.")
    elif has_sum:
        action_type = "AGGREGATE"
        agg_col = aggregate_column
        select_expressions = [f"SUM({agg_col}) AS total_{agg_col}"]
        reasoning.append(f"Identified aggregation: SUM on column '{agg_col}'.")
    elif has_max:
        action_type = "AGGREGATE"
        agg_col = aggregate_column
        select_expressions = [f"MAX({agg_col}) AS max_{agg_col}"]
        reasoning.append(f"Identified aggregation: MAX on column '{agg_col}'.")
    elif has_min:
        action_type = "AGGREGATE"
        agg_col = aggregate_column
        select_expressions = [f"MIN({agg_col}) AS min_{agg_col}"]
        reasoning.append(f"Identified aggregation: MIN on column '{agg_col}'.")
    elif has_count:
        action_type = "AGGREGATE"
        select_expressions = ["COUNT(*) AS total_count"]
        reasoning.append("Identified aggregation: COUNT(*) of matching records.")
    else:
        # Check if specific columns requested (e.g. only names or emails)
        cols_requested = [c for c in entities["columns"] if c != "department"]
        has_explicit_study_year = any(
            phrase in norm_original
            for phrase in ["year of study", "study year", "अभ्यास वर्ष", "शिक्षण वर्ष", "पढ़ाई का वर्ष"]
        )
        if "age" in ent_orig["columns"] and not has_explicit_study_year:
            cols_requested = [column for column in cols_requested if column != "year_of_study"]
        if cols_requested and not any(w in combined_text for w in ["all", "सर्व", "सभी", "संपूर्ण"]):
            action_type = "SELECT_COLUMNS"
            cols = ["name"] if "name" not in cols_requested else []
            cols.extend(cols_requested)
            select_expressions = list(dict.fromkeys(cols))
            reasoning.append(f"Selected specific projection columns: {', '.join(select_expressions)}.")
        else:
            action_type = "SELECT_ALL"
            select_expressions = ["*"]
            reasoning.append("Projecting all columns (*).")

    descending_terms = ["descending", "desc", "उतरत्या क्रमाने", "उतरत्या क्रमात", "घटत्या क्रमाने"]
    ascending_terms = ["ascending", "asc", "चढत्या क्रमाने", "चढत्या क्रमात"]
    is_descending = any(
        re.search(rf"\b{re.escape(term)}\b", combined_text) if term.isascii() else term in combined_text
        for term in descending_terms
    )
    is_ascending = any(
        re.search(rf"\b{re.escape(term)}\b", combined_text) if term.isascii() else term in combined_text
        for term in ascending_terms
    )
    if order_by is None and (is_descending or is_ascending):
        sort_column = next(
            (column for column in ["age", "year_of_study", "gpa", "salary", "name", "id"] if column in ent_orig["columns"]),
            None
        )
        if sort_column is None:
            raise ValueError("Specify which field to sort by, such as age or GPA.")
        direction = "DESC" if is_descending else "ASC"
        order_by = {"column": sort_column, "direction": direction}
        reasoning.append(f"Applied ordering by '{sort_column}' {direction}.")

    # 3. Determine WHERE Filter Conditions
    where_conditions = []

    range_match = re.search(
        r"\bbetween\s+([0-9]+(?:\.[0-9]+)?)\s+and\s+([0-9]+(?:\.[0-9]+)?)"
        r"|([0-9]+(?:\.[0-9]+)?)\s+से\s+([0-9]+(?:\.[0-9]+)?)\s+के\s+बीच"
        r"|([0-9]+(?:\.[0-9]+)?)\s+(?:से|ते)\s+([0-9]+(?:\.[0-9]+)?)(?:\s+(?:वर्ष|साल|उम्र|आयु|वय\w*))?",
        norm_original,
        re.IGNORECASE
    )
    if range_match:
        lower_text = range_match.group(1) or range_match.group(3) or range_match.group(5)
        upper_text = range_match.group(2) or range_match.group(4) or range_match.group(6)
        range_column = next(
            (column for column in ["age", "salary", "gpa", "experience_years", "year_of_study", "budget"] if column in ent_orig["columns"]),
            default_aggregate_column
        )
        lower_value = float(lower_text) if "." in lower_text else int(lower_text)
        upper_value = float(upper_text) if "." in upper_text else int(upper_text)
        where_conditions.extend([
            {"column": range_column, "operator": ">=", "value": lower_value, "value_type": "number"},
            {"column": range_column, "operator": "<=", "value": upper_value, "value_type": "number"}
        ])
        reasoning.append(f"Applied inclusive range filter on '{range_column}'.")

    # A. Department filter
    if entities["departments"]:
        dept_val = entities["departments"][0]
        department_column = "name" if target_table == "departments" else "department"
        where_conditions.append({
            "column": department_column,
            "operator": "=",
            "value": dept_val,
            "value_type": "string"
        })
        reasoning.append(f"Applied department filter: {department_column} = '{dept_val}'.")

    # B. City filter
    if entities["cities"]:
        city_val = entities["cities"][0]
        where_conditions.append({
            "column": "city",
            "operator": "=",
            "value": city_val,
            "value_type": "string"
        })
        reasoning.append(f"Applied filter: city = '{city_val}'.")

    # C. Role filter
    if entities["roles"]:
        role_val = entities["roles"][0]
        where_conditions.append({
            "column": "role",
            "operator": "=",
            "value": role_val,
            "value_type": "string"
        })
        reasoning.append(f"Applied filter: role = '{role_val}'.")

    # D. Numeric conditions (e.g. salary > 80000 or gpa >= 9.0)
    if entities["numbers"] and action_type != "TOP_N" and not range_match:
        num_val = entities["numbers"][0]
        # Decide operator
        op = ">"
        if entities["operators"]:
            op = entities["operators"][0]
        elif any(w in combined_text for w in ["पेक्षा जास्त", "से अधिक", "से ज्यादा", "greater than", "above", "more than"]):
            op = ">"
        elif any(w in combined_text for w in ["पेक्षा कमी", "से कम", "less than", "below"]):
            op = "<"
        elif any(w in combined_text for w in ["किमान", "कम से कम", "at least"]):
            op = ">="
        elif any(w in combined_text for w in ["कमाल", "अधिकतम", "at most"]):
            op = "<="

        # Target numeric column
        target_num_col = None
        if "age" in ent_orig["columns"] or "age" in ent_trans["columns"]:
            target_num_col = "age"
        elif "salary" in ent_orig["columns"] or "salary" in ent_trans["columns"] or (target_table == "employees" and num_val >= 1000):
            target_num_col = "salary"
        elif "gpa" in entities["columns"] or (target_table == "students" and num_val <= 10.0):
            target_num_col = "gpa"
        elif "experience_years" in entities["columns"] or any(w in combined_text for w in ["experience", "अनुभव"]):
            target_num_col = "experience_years"
        elif "year_of_study" in entities["columns"] or any(w in combined_text for w in ["year", "वर्ष", "साल"]):
            target_num_col = "year_of_study"
        elif "budget" in entities["columns"] or target_table == "departments":
            target_num_col = "budget"

        if target_num_col:
            where_conditions.append({
                "column": target_num_col,
                "operator": op,
                "value": num_val,
                "value_type": "number"
            })
            reasoning.append(f"Applied numeric filter: {target_num_col} {op} {num_val}.")

    return {
        "target_table": target_table,
        "action_type": action_type,
        "select_expressions": select_expressions,
        "where_conditions": where_conditions,
        "order_by": order_by,
        "limit": limit,
        "extracted_entities": entities,
        "reasoning": reasoning
    }


if __name__ == "__main__":
    if sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    samples = [
        ("कॉम्प्युटर विभागातील सर्व विद्यार्थी दाखवा", "Show all students where department is 'Computer'", "mr"),
        ("उन कर्मचारियों की सूची दीजिए जिनका वेतन 80000 से अधिक है", "Show salary of employees where salary > 80000", "hi"),
        ("पुण्यातील विद्यार्थ्यांची सरासरी gpa किती आहे?", "Average gpa of students where city is 'Pune'", "mr"),
        ("सर्वोच्च पगार असणारा कर्मचारी कोणता?", "Find employees with highest salary", "mr"),
        ("सिव्हिल विभागाचे प्रमुख कोण आहेत?", "Show hod_name of departments where department is 'Civil'", "mr"),
        ("Show all students from Computer department", "Show all students from Computer department", "en")
    ]

    for orig, trans, lang in samples:
        intent = extract_intent_and_slots(orig, trans, lang)
        print(f"\nQuery: {orig}")
        print(f"Table: {intent['target_table']} | Action: {intent['action_type']}")
        print(f"Columns: {intent['select_expressions']}")
        print(f"Conditions: {intent['where_conditions']}")
        print(f"Order/Limit: {intent['order_by']} / {intent['limit']}")
        print("Reasoning:", "; ".join(intent["reasoning"]))
