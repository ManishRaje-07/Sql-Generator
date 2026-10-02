"""
Master Pipeline Coordinator for Multilingual NL-to-SQL Generator.
Orchestrates:
1. Language Detection
2. Text Normalization and Translation
3. NLP Processing (Tokens, Stopwords, Stemming/Lemmatization)
4. Intent & Entity Extraction
5. Safe SQL Generation & Validation
6. Return generated SQL without database access
"""

import time
from typing import Dict, Any

from nlp.translator import process_translation
from nlp.preprocessor import process_nlp_pipeline
from nlp.intent_extractor import extract_intent_and_slots
from nlp.sql_generator import generate_sql


def process_query_pipeline(
    user_query: str,
    language_override: str = "auto"
) -> Dict[str, Any]:
    """
    Executes the end-to-end 9-step pipeline:
    1. Accept user natural-language question
    2. Detect language
    3. Translate/normalize Hindi & Marathi queries
    4. Process NLP (tokenization, filtering, stemming/lemmatization)
    5. Understand intent (table, columns, conditions)
    6. Generate SQL query
    7. Validate SQL safety
    8. Return SQL without executing it against a database
    """
    total_start = time.time()
    query_clean = user_query.strip()

    if not query_clean:
        return {
            "success": False,
            "error": "Query cannot be empty. Please enter a natural language question.",
            "pipeline": {}
        }

    # Step 1 & 2 & 3: Language Detection, Normalization & Translation
    trans_res = process_translation(query_clean, lang_override=language_override)
    detected_lang = trans_res["detected_language"]
    normalized_text = trans_res["normalized_query"]
    translated_text = trans_res["translated_query"]

    # Step 4: NLP Preprocessing (Tokenization, Stopwords, Stemming/Lemmas)
    nlp_res = process_nlp_pipeline(normalized_text, lang_code=detected_lang["code"])

    if translated_text.upper().startswith(("CREATE DATABASE ", "CREATE TABLE ")):
        sql_query = translated_text.rstrip("; ") + ";"
        return {
            "success": True,
            "input_query": query_clean,
            "language": detected_lang,
            "translation": {
                "translated_query": translated_text,
                "source": trans_res["translation_source"],
                "is_translated": trans_res["is_translated"]
            },
            "nlp_breakdown": {
                "raw_tokens": nlp_res["raw_tokens"],
                "filtered_tokens": nlp_res["filtered_tokens"],
                "lemmatized_tokens": nlp_res["lemmatized_tokens"],
                "steps": nlp_res["steps_log"]
            },
            "intent": None,
            "sql": {
                "query": sql_query,
                "formatted": sql_query,
                "is_safe": True,
                "validation_error": None,
                "clauses": {}
            },
            "total_latency_ms": round((time.time() - total_start) * 1000, 2)
        }

    # Step 5: Intent & Entity Extraction
    try:
        intent = extract_intent_and_slots(
            original_query=query_clean,
            translated_query=translated_text,
            lang_code=detected_lang["code"]
        )
    except ValueError as ve:
        return {
            "success": False,
            "error": str(ve),
            "input_query": query_clean,
            "language": detected_lang,
            "sql": {"query": "", "formatted": "", "is_safe": False, "validation_error": str(ve), "clauses": {}},
            "translation": trans_res,
            "nlp_breakdown": nlp_res,
            "intent": None,
            "total_latency_ms": round((time.time() - total_start) * 1000, 2)
        }

    # Step 6 & 7: SQL Generation & Safety Validation
    sql_res = generate_sql(intent)

    total_time_ms = round((time.time() - total_start) * 1000, 2)

    return {
        "success": True,
        "input_query": query_clean,
        "language": detected_lang,
        "translation": {
            "translated_query": translated_text,
            "source": trans_res["translation_source"],
            "is_translated": trans_res["is_translated"]
        },
        "nlp_breakdown": {
            "raw_tokens": nlp_res["raw_tokens"],
            "filtered_tokens": nlp_res["filtered_tokens"],
            "lemmatized_tokens": nlp_res["lemmatized_tokens"],
            "steps": nlp_res["steps_log"]
        },
        "intent": {
            "target_table": intent["target_table"],
            "action_type": intent["action_type"],
            "select_expressions": intent["select_expressions"],
            "where_conditions": intent["where_conditions"],
            "order_by": intent["order_by"],
            "limit": intent["limit"],
            "extracted_entities": intent["extracted_entities"],
            "reasoning": intent["reasoning"]
        },
        "sql": {
            "query": sql_res["sql"],
            "formatted": sql_res["formatted_sql"],
            "is_safe": sql_res["is_safe"],
            "validation_error": sql_res["validation_error"],
            "clauses": sql_res["clauses"]
        },
        "total_latency_ms": total_time_ms
    }


if __name__ == "__main__":
    import sys
    if sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    test_query = "कॉम्प्युटर विभागातील सर्व विद्यार्थी दाखवा"
    res = process_query_pipeline(test_query)
    print("Input:", res["input_query"])
    print("Detected Language:", res["language"]["name"])
    print("Translated Query:", res["translation"]["translated_query"])
    print("Generated SQL:", res["sql"]["query"])
