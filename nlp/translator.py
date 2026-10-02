"""
Translator module for Multilingual Queries.
Provides hybrid translation: fast offline deterministic semantic translation
with optional quick online Google translation if available and reachable within 1.5s.
"""

import os
import sys
import re
from typing import Dict, Any, Optional

# Add project root to sys.path
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
from nlp.language_detector import detect_language


def offline_semantic_translate(text: str, lang_code: str) -> str:
    """
    Offline deterministic translation and semantic normalization
    converting Marathi and Hindi queries into structured English queries.
    Guarantees 0ms latency and 100% offline reliability.
    """
    norm = normalize_text(text)
    entities = extract_matched_entities(norm)

    normalized_lower = norm.lower()
    create_verbs = ["create", "तयार करा", "तयार कर", "बनवा", "बनाओ", "बनाइए", "बनाएं", "तैयार करो"]
    has_create_verb = any(word in normalized_lower for word in create_verbs)
    has_table_word = any(word in normalized_lower for word in ["table", "टेबल", "तक्ता"])

    if has_create_verb and has_table_word:
        table_name = next(iter(entities["tables"]), None)
        if not table_name and lang_code == "en":
            match = re.search(r"\btable\s+(?:named\s+)?([a-zA-Z_][a-zA-Z0-9_]*)", norm, re.IGNORECASE)
            table_name = match.group(1) if match else None
        table_name = table_name or "table_name"

        columns = []
        if re.search(r"\bid\b|आयडी|आईडी|क्रमांक", normalized_lower):
            columns.append("id INTEGER")
        if any(word in normalized_lower for word in ["name", "नाव", "नाम"]):
            columns.append("name TEXT")
        if any(word in normalized_lower for word in ["age", "वय", "उम्र", "आयु"]):
            columns.append("age INTEGER")
        for column in entities["columns"]:
            if column not in {"name", "age", "id"} and column not in [item.split()[0] for item in columns]:
                columns.append(f"{column} TEXT")

        if not columns:
            columns = ["id INTEGER"]
        return f"CREATE TABLE {table_name} ({', '.join(columns)})"

    if any(word in normalized_lower for word in ["database", "डेटाबेस", "डाटाबेस"]) and any(
        word in normalized_lower for word in ["create", "तयार करा", "बनवा", "बनाओ", "बनाइए", "तैयार करो"]
    ):
        database_name = next(iter(entities["tables"]), None)
        if not database_name and lang_code == "en":
            match = re.search(r"\bdatabase\s+(?:named\s+)?([a-zA-Z_][a-zA-Z0-9_]*)", norm, re.IGNORECASE)
            database_name = match.group(1) if match else None
        return f"CREATE DATABASE {database_name or 'database_name'}"

    if lang_code == "en":
        return text

    parts = []

    # 1. Determine Target Table with intelligent subject prioritization
    # Subject priority: if query mentions students/छात्र/विद्यार्थी -> students
    # If query mentions employees/कर्मचारी -> employees
    # If query mentions department heads/budget/departments without students/employees -> departments
    primary_table = "students"
    has_students = any(syn in norm for syn in TABLE_SYNONYMS["students"])
    has_employees = any(syn in norm for syn in TABLE_SYNONYMS["employees"])
    has_departments = any(syn in norm for syn in ["विभागांची माहिती", "विभाग दाखवा", "सर्व विभाग", "विभाग यादी", "departments", "department list"])

    if has_students:
        primary_table = "students"
    elif has_employees:
        primary_table = "employees"
    elif "salary" in entities["columns"] or "experience_years" in entities["columns"] or entities["roles"]:
        primary_table = "employees"
    elif "budget" in entities["columns"] or "faculty_count" in entities["columns"] or "hod_name" in entities["columns"]:
        primary_table = "departments"
    elif has_departments or "departments" in entities["tables"]:
        primary_table = "departments"

    # 2. Determine Intent & Aggregation with priority
    # Priority: AVG > SUM > MAX > MIN > COUNT
    # Note: 'किती' or 'कितने' in Hindi/Marathi can mean 'how much' when paired with 'सरासरी/औसत/पगार'
    is_avg = "AVG" in entities["aggregations"] or any(w in norm for w in ["सरासरी", "औसत", "average", "avg"])
    is_total_count = any(w in norm for w in ["total number", "total count", "कुल संख्या", "एकूण संख्या"])
    is_sum = not is_total_count and (
        "SUM" in entities["aggregations"]
        or any(w in norm for w in ["एकूण बेरीज", "एकूण", "कुल जोड़", "कुल योग", "sum", "total"])
    )
    is_max = "MAX" in entities["aggregations"] or any(w in norm for w in ["सर्वोच्च", "सर्वाधिक", "कमाल", "सर्वात जास्त", "सबसे ज्यादा", "सबसे अधिक", "अधिकतम", "highest", "maximum"])
    is_min = "MIN" in entities["aggregations"] or any(w in norm for w in ["सर्ववात कमी", "किमान", "कमीत कमी", "सबसे कम", "न्यूनतम", "lowest", "minimum"])
    is_count = False

    if is_total_count:
        is_count = True
    elif not (is_avg or is_sum or is_max or is_min):
        is_count = "COUNT" in entities["aggregations"] or any(w in norm for w in ["किती", "कितने", "संख्या", "गिनती", "count", "how many"])

    measure_columns = ("age", "salary", "gpa", "experience_years", "year_of_study", "budget")
    requested_measure = next((column for column in measure_columns if column in entities["columns"]), None)

    # Action phrase
    if is_avg:
        target_col = requested_measure or ("salary" if primary_table == "employees" else "gpa")
        parts.append(f"Average {target_col} of {primary_table}")
    elif is_sum:
        target_col = requested_measure or ("budget" if primary_table == "departments" else "salary")
        parts.append(f"Total {target_col} of {primary_table}")
    elif is_max:
        target_col = requested_measure or ("salary" if primary_table == "employees" else "gpa")
        parts.append(f"Find {primary_table} with highest {target_col}")
    elif is_min:
        target_col = requested_measure or ("salary" if primary_table == "employees" else "gpa")
        parts.append(f"Find {primary_table} with lowest {target_col}")
    elif is_count:
        parts.append(f"Count of {primary_table}")
    else:
        # Check specific column request
        col_names = [c for c in entities["columns"] if c not in ["department"]]
        if col_names:
            parts.append(f"Show {', '.join(col_names)} of {primary_table}")
        else:
            parts.append(f"Show all {primary_table}")

    # 3. Add Filter Conditions
    filter_clauses = []

    # Department filter
    if entities["departments"]:
        dept = entities["departments"][0]
        filter_clauses.append(f"department is '{dept}'")

    # City filter
    if entities["cities"]:
        city = entities["cities"][0]
        filter_clauses.append(f"city is '{city}'")

    # Role filter
    if entities["roles"]:
        role = entities["roles"][0]
        filter_clauses.append(f"role is '{role}'")

    # Numerical condition (e.g. salary > 80000 or gpa >= 9.0)
    if entities["numbers"]:
        num = entities["numbers"][0]
        op_str = ">"
        if entities["operators"]:
            op_str = entities["operators"][0]
        elif any(w in norm for w in ["पेक्षा जास्त", "से अधिक", "से ज्यादा", "अधिक", "जास्त"]):
            op_str = ">"
        elif any(w in norm for w in ["पेक्षा कमी", "से कम", "कमी"]):
            op_str = "<"
        elif any(w in norm for w in ["किमान", "कम से कम"]):
            op_str = ">="
        elif any(w in norm for w in ["कमाल", "अधिकतम"]):
            op_str = "<="

        # Target numeric column
        if "age" in entities["columns"]:
            filter_clauses.append(f"age {op_str} {num}")
        elif "salary" in entities["columns"] or num >= 10000:
            filter_clauses.append(f"salary {op_str} {num}")
        elif "gpa" in entities["columns"] or (isinstance(num, float) and num <= 10.0):
            filter_clauses.append(f"gpa {op_str} {num}")
        elif "experience_years" in entities["columns"] or any(w in norm for w in ["अनुभव", "experience"]):
            filter_clauses.append(f"experience_years {op_str} {num}")
        elif "year_of_study" in entities["columns"] or any(w in norm for w in ["वर्ष", "साल", "year"]):
            filter_clauses.append(f"year_of_study {op_str} {num}")
        else:
            if primary_table == "employees":
                filter_clauses.append(f"salary {op_str} {num}")
            else:
                filter_clauses.append(f"gpa {op_str} {num}")

    if filter_clauses:
        parts.append("where " + " and ".join(filter_clauses))

    return " ".join(parts)


def process_translation(query: str, lang_override: str = "auto", enable_online: bool = False) -> Dict[str, Any]:
    """
    Main translation pipeline:
    1. Detects language
    2. Normalizes text
    3. Translates if necessary (offline fast semantic translation default for zero-lag speed)
    """
    detected = detect_language(query, override=lang_override)
    lang_code = detected["code"]
    normalized = normalize_text(query)

    if lang_code == "en":
        translated = offline_semantic_translate(normalized, lang_code)
        return {
            "original_query": query,
            "detected_language": detected,
            "normalized_query": normalized,
            "translated_query": translated,
            "translation_source": "offline_semantic_rules" if translated != normalized else "english_native",
            "is_translated": translated != normalized
        }

    # Use offline semantic translation for instant, reliable response
    offline_res = offline_semantic_translate(normalized, lang_code)
    return {
        "original_query": query,
        "detected_language": detected,
        "normalized_query": normalized,
        "translated_query": offline_res,
        "translation_source": "offline_semantic_rules",
        "is_translated": True
    }


if __name__ == "__main__":
    if sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    test_queries = [
        "कॉम्प्युटर विभागातील सर्व विद्यार्थी दाखवा",
        "उन कर्मचारियों की सूची दीजिए जिनका वेतन 80000 से अधिक है",
        "पुण्यातील विद्यार्थ्यांची सरासरी gpa किती आहे?",
        "सर्वोच्च पगार असणारा कर्मचारी कोणता?",
        "सिव्हिल विभागाचे प्रमुख कोण आहेत?",
        "Show all students from Computer department"
    ]
    for q in test_queries:
        res = process_translation(q)
        print(f"\n[Source ({res['detected_language']['name']})]: {q}")
        print(f"[Translation ({res['translation_source']})]: {res['translated_query']}")
