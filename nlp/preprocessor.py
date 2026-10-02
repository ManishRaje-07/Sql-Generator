"""
NLP Preprocessor module.
Implements tokenization, stopword filtering, stemming, and lemmatization
for English, Hindi, and Marathi queries.
"""

import os
import sys
import re
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Domain stopwords that don't carry SQL condition meaning
# Note: words like 'average', 'count', 'max', 'min', 'greater', 'less' are preserved
ENGLISH_STOPWORDS = {
    "please", "kindly", "can", "you", "show", "give", "display", "list", "tell", "find",
    "get", "me", "the", "a", "an", "is", "are", "was", "were", "of", "in", "from",
    "with", "and", "or", "for", "to", "at", "who", "which", "what", "whose", "details",
    "information", "record", "records", "data"
}

HINDI_STOPWORDS = {
    "कृपया", "दिखाओ", "दिखाइए", "बताओ", "बताइए", "दीजिए", "करो", "करें", "ढूंढो", "ढूंढिए",
    "सूची", "दो", "है", "हैं", "था", "थी", "थे", "का", "के", "की", "को", "में", "से",
    "पर", "लिए", "वाले", "वाली", "जिनका", "जिनकी", "जिनके", "कौन", "किसका", "विवरण", "जानकारी"
}

MARATHI_STOPWORDS = {
    "कृपया", "दाखवा", "सांगा", "द्या", "करा", "शोधा", "यादी", "काढा", "आहे", "आहेत",
    "होते", "होती", "होता", "असावे", "असणाऱ्या", "असणारे", "असलेले", "च्या", "चे", "ची",
    "चा", "ला", "ना", "तून", "कडे", "साठी", "कोणते", "कोणता", "कोणती", "कोणाचा", "कोणाचे",
    "तपशील", "माहिती"
}

# Indic Suffix stripping rules for Marathi and Hindi morphological inflection reduction
INDIC_SUFFIX_MAP = [
    # Marathi complex postpositional inflections
    (r'विभागातील$', 'विभाग'),
    (r'विभागात$', 'विभाग'),
    (r'विभागांची$', 'विभाग'),
    (r'विभागांचे$', 'विभाग'),
    (r'विभागांचा$', 'विभाग'),
    (r'विद्यार्थ्यांची$', 'विद्यार्थी'),
    (r'विद्यार्थ्यांना$', 'विद्यार्थी'),
    (r'विद्यार्थ्यांचे$', 'विद्यार्थी'),
    (r'विद्यार्थींची$', 'विद्यार्थी'),
    (r'कर्मचाऱ्यांचे$', 'कर्मचारी'),
    (r'कर्मचाऱ्यांचा$', 'कर्मचारी'),
    (r'कर्मचाऱ्यांची$', 'कर्मचारी'),
    (r'कर्मचाऱ्यांना$', 'कर्मचारी'),
    (r'कर्मचार्यांचे$', 'कर्मचारी'),
    (r'पुण्यातील$', 'पुणे'),
    (r'पुण्यात$', 'पुणे'),
    (r'मुंबईतील$', 'मुंबई'),
    (r'मुंबईत$', 'मुंबई'),
    (r'दिल्लीतील$', 'दिल्ली'),
    (r'दिल्लीत$', 'दिल्ली'),
    (r'साताऱ्यातील$', 'सातारा'),
    (r'कोल्हापुरातील$', 'कोल्हापूर'),
    (r'नाशिकमधील$', 'नाशिक'),
    (r'शिक्षकांची$', 'शिक्षक'),
    (r'प्राध्यापकांची$', 'प्राध्यापक'),
    (r'अध्यापकों$', 'अध्यापक'),
    # Hindi plural/case inflections
    (r'छात्रों$', 'छात्र'),
    (r'कर्मचारियों$', 'कर्मचारी'),
    (r'विभागों$', 'विभाग'),
    (r'शिक्षकों$', 'शिक्षक'),
    # General suffixes
    (r'तील$', ''),
    (r'मधील$', ''),
    (r'तून$', ''),
    (r'च्या$', ''),
    (r'चे$', ''),
    (r'ची$', ''),
    (r'चा$', ''),
    (r'ना$', ''),
    (r'ला$', '')
]


def tokenize(text: str) -> List[str]:
    """
    Tokenizes text into words and alphanumeric tokens,
    preserving numbers, decimals, and words in Latin or Devanagari.
    """
    # Regex splits words, retaining Devanagari and Latin words, decimals, and operators
    tokens = re.findall(r'[\u0900-\u097F\w]+(?:\.\d+)?|[><=!]+', text.strip())
    return [t for t in tokens if t.strip()]


def filter_stopwords(tokens: List[str], lang_code: str = "en") -> List[str]:
    """Filters out non-content stopwords based on language."""
    if lang_code == "mr":
        stops = MARATHI_STOPWORDS
    elif lang_code == "hi":
        stops = HINDI_STOPWORDS
    else:
        stops = ENGLISH_STOPWORDS

    return [t for t in tokens if t.lower() not in stops and t not in stops]


def stem_indic_token(token: str) -> str:
    """Stems/lemmatizes Indic tokens by stripping inflectional suffixes."""
    word = token
    for pattern, replacement in INDIC_SUFFIX_MAP:
        if re.search(pattern, word):
            word = re.sub(pattern, replacement, word)
            break
    return word


def stem_english_token(token: str) -> str:
    """Simple English stemmer/lemmatizer rule engine."""
    word = token.lower()
    # Common noun plurals
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("es") and len(word) > 4:
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    # Common superlative / comparative
    if word.endswith("est") and len(word) > 5:
        return word[:-3]
    if word.endswith("er") and len(word) > 4:
        return word[:-2]
    return word


def process_nlp_pipeline(query: str, lang_code: str = "en") -> Dict[str, Any]:
    """
    Full NLP Pipeline step execution:
    1. Tokenization
    2. Stopword Filtering
    3. Stemming & Lemmatization
    Returns intermediate results for transparency and UI visualization.
    """
    raw_tokens = tokenize(query)
    filtered = filter_stopwords(raw_tokens, lang_code)

    stemmed = []
    lemmatized = []

    for t in filtered:
        if lang_code in ["mr", "hi"]:
            s = stem_indic_token(t)
            stemmed.append(s)
            lemmatized.append(s)  # Indic root stem serves as lemma
        else:
            s = stem_english_token(t)
            stemmed.append(s)
            lemmatized.append(s)

    return {
        "raw_tokens": raw_tokens,
        "token_count": len(raw_tokens),
        "filtered_tokens": filtered,
        "filtered_count": len(filtered),
        "stemmed_tokens": stemmed,
        "lemmatized_tokens": lemmatized,
        "steps_log": [
            f"Step 1 [Tokenization]: Extracted {len(raw_tokens)} tokens from query.",
            f"Step 2 [Stopword Filtering]: Removed non-content filler words, retained {len(filtered)} meaningful tokens.",
            f"Step 3 [Morphological Stemming]: Converted inflected words to root dictionary lemmas ({', '.join(lemmatized[:5])})."
        ]
    }


if __name__ == "__main__":
    if sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    test_samples = [
        ("कॉम्प्युटर विभागातील सर्व विद्यार्थी दाखवा", "mr"),
        ("उन कर्मचारियों की सूची दीजिए जिनका वेतन 80000 से अधिक है", "hi"),
        ("Show all students from Computer department", "en")
    ]

    for q, lang in test_samples:
        print(f"\nOriginal ({lang}): {q}")
        res = process_nlp_pipeline(q, lang)
        print("Raw Tokens:", res["raw_tokens"])
        print("Filtered Tokens:", res["filtered_tokens"])
        print("Lemmas/Stems:", res["lemmatized_tokens"])
        for s in res["steps_log"]:
            print(" ", s)
