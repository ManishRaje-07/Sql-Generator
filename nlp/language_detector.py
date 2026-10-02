"""
Language Detector module.
Detects English, Hindi, and Marathi natural language text using script inspection
and lexical frequency heuristics. Supports user overrides and confidence scoring.
"""

import re
from typing import Dict, Any

LANGUAGES = {
    "en": {"code": "en", "name": "English", "native_name": "English"},
    "hi": {"code": "hi", "name": "Hindi", "native_name": "हिन्दी"},
    "mr": {"code": "mr", "name": "Marathi", "native_name": "मराठी"}
}

# Distinctive lexical markers for Marathi
MARATHI_MARKERS = {
    # Postpositions & suffixes
    "विभागातील", "मधील", "तील", "च्या", "चे", "ची", "चा", "ला", "ना", "तून", "कडे", "साठी",
    "पेक्षा", "खालील", "वरील", "जवळ",
    # Verbs and auxiliary
    "आहे", "आहेत", "दाखवा", "सांगा", "द्या", "करा", "शोधा", "यादी", "काढा", "असावे", "असणाऱ्या",
    # Vocabulary
    "विद्यार्थी", "विद्यार्थ्यांची", "विद्यार्थ्यांना", "विद्यार्थ्यांचे", "विद्यार्थींची",
    "कर्मचारी", "कर्मचाऱ्यांचे", "कर्मचाऱ्यांचा", "कर्मचाऱ्यांची", "कामगार", "नोकर",
    "पगार", "मानधन", "जास्त", "कमी", "सर्व", "सर्वच", "किती", "कोणते", "कोणता", "कोणती",
    "कोणाचा", "कोणाचे", "कोणाला", "नावे", "नाव", "प्राध्यापक", "शिक्षक", "वर्ष", "इयत्ता"
}

# Distinctive lexical markers for Hindi
HINDI_MARKERS = {
    # Postpositions
    "में", "के", "की", "का", "को", "से", "पर", "लिए", "तक",
    # Verbs and auxiliary
    "है", "हैं", "दिखाओ", "दिखाइए", "बताओ", "बताइए", "दीजिए", "करो", "ढूंढो", "ढूंढिए", "सूची",
    # Vocabulary
    "छात्र", "छात्रों", "विद्यार्थियों", "कर्मचारी", "कर्मचारियों",
    "वेतन", "तनख्वाह", "ज्यादा", "अधिक", "कम", "सभी", "सारे", "कितने", "कितनी", "कितना",
    "कौन", "किसका", "किसके", "किसकी", "नाम", "साल"
}


def detect_language(text: str, override: str = "auto") -> Dict[str, Any]:
    """
    Detects if the query is in English, Hindi, or Marathi.
    If override is specified (e.g. 'en', 'hi', 'mr'), uses that while checking validity.
    """
    cleaned = text.strip()
    if not cleaned:
        return {
            "code": "en",
            "name": "English",
            "native_name": "English",
            "confidence": 1.0,
            "detected_by": "default_empty"
        }

    # If manual override requested and valid
    if override in LANGUAGES:
        info = LANGUAGES[override]
        return {
            "code": info["code"],
            "name": info["name"],
            "native_name": info["native_name"],
            "confidence": 1.0,
            "detected_by": "user_override"
        }

    # Count scripts
    latin_chars = len(re.findall(r'[a-zA-Z]', cleaned))
    devanagari_chars = len(re.findall(r'[\u0900-\u097F]', cleaned))

    # Predominantly Latin script -> English
    if devanagari_chars == 0 and latin_chars > 0:
        return {
            "code": "en",
            "name": "English",
            "native_name": "English",
            "confidence": 0.99,
            "detected_by": "latin_script"
        }

    if devanagari_chars > latin_chars:
        # Both Marathi and Hindi use Devanagari script.
        # Use lexical word and n-gram matching.
        words = re.findall(r'[\u0900-\u097F]+', cleaned.lower())
        
        mr_score = 0
        hi_score = 0

        for word in words:
            if word in MARATHI_MARKERS:
                mr_score += 2
            elif any(word.endswith(suffix) for suffix in ["तील", "मधील", "च्या", "चे", "ची", "चा", "ला", "ना", "पेक्षा"]):
                mr_score += 1.5

            if word in HINDI_MARKERS:
                hi_score += 2
            elif any(word.endswith(suffix) for suffix in ["ों", "एं", "कर", "ाना", "ाओ", "ाइए"]):
                hi_score += 1.5

        # Check for distinctive letters
        # 'ळ' (0x0933) is widely used in Marathi and very rare in standard Hindi
        if 'ळ' in cleaned:
            mr_score += 3

        if mr_score > hi_score:
            total = mr_score + hi_score or 1
            conf = min(0.99, round(0.60 + (mr_score / (total * 2)), 2))
            return {
                "code": "mr",
                "name": "Marathi",
                "native_name": "मराठी",
                "confidence": conf,
                "detected_by": "lexical_heuristics"
            }
        elif hi_score > mr_score:
            total = mr_score + hi_score or 1
            conf = min(0.99, round(0.60 + (hi_score / (total * 2)), 2))
            return {
                "code": "hi",
                "name": "Hindi",
                "native_name": "हिन्दी",
                "confidence": conf,
                "detected_by": "lexical_heuristics"
            }
        else:
            # Default Devanagari tie-break: check if any Marathi character or words like "विद्यार्थी"
            # In university/college contexts in Maharashtra, Marathi is default or 50/50
            return {
                "code": "mr",
                "name": "Marathi",
                "native_name": "मराठी",
                "confidence": 0.70,
                "detected_by": "script_fallback"
            }

    # Fallback to English
    return {
        "code": "en",
        "name": "English",
        "native_name": "English",
        "confidence": 0.85,
        "detected_by": "general_fallback"
    }


if __name__ == "__main__":
    import sys
    if sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    test_queries = [
        "कॉम्प्युटर विभागातील सर्व विद्यार्थी दाखवा",
        "कंप्यूटर विभाग के सभी छात्र दिखाओ",
        "Show all students from Computer department",
        "पुण्यातील विद्यार्थ्यांची यादी सांगा",
        "उन कर्मचारियों की सूची दीजिए जिनका वेतन 80000 से अधिक है",
        "Highest salary in IT department"
    ]
    for q in test_queries:
        res = detect_language(q)
        print(f"'{q}' -> {res['name']} ({res['confidence']*100:.0f}%) via {res['detected_by']}")

