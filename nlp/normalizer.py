"""
Normalizer module for Indic (Marathi, Hindi) and English text.
Performs Unicode normalization, Devanagari numerals conversion,
entity canonicalization, and dictionary-based keyword mapping.
"""

import re
import unicodedata
from typing import Dict, Any, List, Tuple

# Devanagari numerals to ASCII digits
DEVANAGARI_DIGITS = {
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
}

# Number words in Marathi & Hindi
WORD_NUMBERS = {
    "एक": 1, "दोन": 2, "दो": 2, "तीन": 3, "चार": 4, "पाच": 5, "पांच": 5,
    "सहा": 6, "छह": 6, "सात": 7, "आठ": 8, "नऊ": 9, "नौ": 9, "दहा": 10, "दस": 10,
    "पंधरा": 15, "पंद्रह": 15, "वीस": 20, "बीस": 20, "पन्नास": 50, "पचास": 50,
    "शंभर": 100, "सौ": 100, "हजार": 1000, "लाख": 100000
}

# Table synonyms
TABLE_SYNONYMS = {
    "students": [
        "विद्यार्थी", "विद्यार्थ्यांची", "विद्यार्थ्यांना", "विद्यार्थ्यांचे", "विद्यार्थींची",
        "छात्र", "छात्रों", "विद्यार्थियों", "छात्रो",
        "students", "student", "pupils", "learners"
    ],
    "departments": [
        "विभाग", "विभागातील", "विभागांची", "विभागांचे", "विभागांचा", "विभागात",
        "डिपार्टमेंट", "डिपार्टमेंट्स", "विभागो", "विभागों",
        "departments", "department", "dept", "depts", "branches", "branch"
    ],
    "employees": [
        "कर्मचारी", "कर्मचाऱ्यांचे", "कर्मचाऱ्यांचा", "कर्मचाऱ्यांची", "कर्मचाऱ्यांना",
        "कर्मचार्यांचे", "कामगार", "नोकर", "कर्मचारियों", "कर्मचारियो",
        "employees", "employee", "staff", "workers", "faculty", "teachers", "प्राध्यापक", "शिक्षक"
    ]
}

# Column synonyms
COLUMN_SYNONYMS = {
    "name": [
        "name", "नाव", "नावाचे", "नावाची यादी", "नावे सांगा", "नाव काय", "नाव सांग", "नाम", "नाम बताओ", "नाम दिखाओ", "names", "student name", "employee name"
    ],
    "age": ["वय", "वयानुसार", "उम्र", "आयु", "age"],
    "department": [
        "विभाग", "डिपार्टमेंट", "शाखा", "ब्रांच", "department", "dept", "branch"
    ],
    "gpa": [
        "जीपीए", "सीजीपीए", "गुण", "मार्क्स", "अंक", "श्रेणी", "gpa", "cgpa", "marks", "score", "grade"
    ],
    "salary": [
        "पगार", "वेतन", "सॅलरी", "मानधन", "तनख्वाह", "मासिक वेतन", "salary", "pay", "compensation", "income", "package"
    ],
    "year_of_study": [
        "वर्ष", "इयत्ता", "वर्ग", "साल", "शिकणारे वर्ष", "अभ्यास वर्ष", "year", "year of study", "grade year", "class"
    ],
    "experience_years": [
        "अनुभव", "कामाचा अनुभव", "अनुभवी", "तजुर्बा", "experience", "exp", "years of experience", "work experience"
    ],
    "city": [
        "शहर", "गाव", "ठिकाण", "राहण्याचे ठिकाण", "स्थान", "नगर", "city", "location", "town", "place"
    ],
    "budget": [
        "बजेट", "अर्थसंकल्प", "निधी", "खर्च", "अनुदान", "budget", "funds", "budget allocation"
    ],
    "faculty_count": [
        "प्राध्यापक संख्या", "शिक्षक संख्या", "फॅकल्टी", "शिक्षकांची संख्या", "शिक्षकांची", "प्राध्यापकांची संख्या",
        "अध्यापकों की संख्या", "faculty count", "teachers count", "number of teachers", "professors count"
    ],
    "hod_name": [
        "विभाग प्रमुख", "एचओडी", "विभागप्रमुख", "प्रमुख", "अध्यक्ष", "hod", "head of department", "hod name", "head"
    ],
    "role": [
        "पद", "हुद्दा", "काम", "डेसिग्नेशन", "भूमिका", "role", "designation", "job title", "position", "post"
    ],
    "email": [
        "ईमेल", "ई-मेल", "मेल", "email", "e-mail", "mail"
    ]
}

# Department values mapping
DEPARTMENT_VALUES = {
    "Computer": [
        "कॉम्प्युटर", "कंप्यूटर", "कम्प्यूटर", "संगणक", "संगणकशास्त्र", "कंप्यूटर साइंस", "computer", "cs", "cse"
    ],
    "IT": [
        "आयटी", "आय.टी.", "माहिती तंत्रज्ञान", "सूचना प्रौद्योगिकी", "it", "information technology"
    ],
    "Mechanical": [
        "मेकॅनिकल", "मैकेनिकल", "यांत्रिकी", "mechanical", "mech"
    ],
    "Civil": [
        "सिव्हिल", "सिविल", "स्थापत्य", "civil"
    ],
    "Electrical": [
        "इलेक्ट्रिकल", "विद्युत", "बिजली", "electrical", "ee"
    ],
    "HR": [
        "एचआर", "एच.आर.", "मानव संसाधन", "hr", "human resources"
    ],
    "Finance": [
        "फायनान्स", "वित्त", "आर्थिक", "finance"
    ],
    "Marketing": [
        "मार्केटिंग", "विपणन", "marketing"
    ]
}

# City values mapping
CITY_VALUES = {
    "Pune": ["पुणे", "पुण्यातील", "पुण्यात", "पूना", "pune", "poona"],
    "Mumbai": ["मुंबई", "मुंबईतील", "मुंबईत", "बॉम्बे", "mumbai", "bombay"],
    "Delhi": ["दिल्ली", "दिल्लीतील", "दिल्लीत", "नई दिल्ली", "delhi", "new delhi"],
    "Bangalore": ["बंगळुरू", "बैंगलोर", "बेंगलुरु", "बेंगलोर", "bangalore", "bengaluru"],
    "Nagpur": ["नागपूर", "नागपुरात", "नागपुर", "nagpur"],
    "Nashik": ["नाशिक", "नाशिकमधील", "नासिक", "nashik", "nasik"],
    "Satara": ["सातारा", "साताऱ्यातील", "सातार्यात", "satara"],
    "Kolhapur": ["कोल्हापूर", "कोल्हापुरातील", "kolhapur"],
    "Solapur": ["सोलापूर", "सोलापुरातील", "solapur"]
}

# Role values mapping
ROLE_VALUES = {
    "Professor": ["प्रोफेसर", "प्राध्यापक", "professor"],
    "Assistant Professor": ["असिस्टंट प्रोफेसर", "सहाय्यक प्राध्यापक", "सहायक प्राध्यापक", "assistant professor"],
    "Associate Professor": ["असोसिएट प्रोफेसर", "सह प्राध्यापक", "सह-प्राध्यापक", "associate professor"],
    "Software Engineer": ["सॉफ्टवेअर इंजिनिअर", "सॉफ्टवेयर इंजीनियर", "software engineer", "dev"],
    "Senior Manager": ["सीनियर मॅनेजर", "वरिष्ठ प्रबंधक", "senior manager"],
    "Data Analyst": ["डेटा ॲनालिस्ट", "डेटा एनालिस्ट", "data analyst"],
    "AI Specialist": ["एआय स्पेशलिस्ट", "ai specialist", "ai engineer"],
    "Lab Technician": ["लॅब टेक्निशियन", "प्रयोगशाला तकनीशियन", "lab technician"],
    "HR Executive": ["एचआर एक्झिक्युटिव्ह", "hr executive"],
    "Chief Accountant": ["चीफ अकाउंटंट", "मुख्य लेखाकार", "chief accountant"],
    "Financial Analyst": ["फायनान्शियल ॲनालिस्ट", "financial analyst"]
}

# Comparison operators mapping
OPERATOR_PATTERNS = [
    (">=", [
        "किमान", "कमीत कमी", "कमीत-कमी", "किमानपक्षी", "कम से कम", "न्यूनतम",
        "at least", "minimum of", "greater than or equal to", ">="
    ]),
    ("<=", [
        "जास्तीत जास्त", "जास्तीत-जास्त", "कमाल", "अधिक से अधिक", "अधिकतम",
        "at most", "maximum of", "less than or equal to", "<="
    ]),
    (">", [
        "पेक्षा जास्त", "पेक्षा अधिक", "पेक्षा मोठे", "जास्त", "अधिक", "मोठे",
        "से अधिक", "से ज्यादा", "से बड़ा", "ज्यादा", "बड़ा",
        "greater than", "more than", "above", "exceeding", "higher than", "greater", ">"
    ]),
    ("<", [
        "पेक्षा कमी", "पेक्षा लहान", "कमी", "लहान",
        "से कम", "से छोटा", "कम", "छोटा",
        "less than", "fewer than", "under", "below", "smaller than", "less", "<"
    ]),
    ("!=", [
        "सोडून", "व्यतिरिक्त", "च्याशिवाय", "नसलेले", "के अलावा", "के बिना", "छोड़कर",
        "not equal to", "not in", "except", "excluding", "!=", "different from"
    ]),
    ("=", [
        "समान", "बरोबर", "सारखे", "असणारे", "असलेले", "बराबर", "हो", "equal to", "equals", "equal", "exactly", "="
    ])
]

# Aggregation patterns mapping
AGGREGATION_PATTERNS = [
    ("COUNT", [
        "किती", "संख्या", "मोजा", "एकूण संख्या", "गणना", "कितने", "कितनी", "गिनती", "कुल संख्या",
        "count", "how many", "number of", "total count", "quantity"
    ]),
    ("AVG", [
        "सरासरी", "मध्यम", "औसत", "average", "avg", "mean"
    ]),
    ("SUM", [
        "एकूण बेरीज", "एकूण", "एकंदर", "कुल जोड़", "कुल योग", "कुल", "sum", "total", "overall"
    ]),
    ("MAX", [
        "सर्वोच्च", "सर्वाधिक", "कमाल", "सर्वात जास्त", "जास्तीत जास्त", "मोठ्यात मोठे",
        "सबसे ज्यादा", "सबसे अधिक", "अधिकतम", "सबसे बड़ा",
        "highest", "maximum", "max", "top", "best", "greatest", "most"
    ]),
    ("MIN", [
        "सर्वात कमी", "किमान", "कमीत कमी", "लहानात लहान",
        "सबसे कम", "न्यूनतम", "सबसे छोटा",
        "lowest", "minimum", "min", "least", "bottom", "smallest"
    ])
]


def convert_devanagari_numerals(text: str) -> str:
    """Converts Devanagari numerals (०-९) to ASCII digits (0-9)."""
    return "".join(DEVANAGARI_DIGITS.get(ch, ch) for ch in text)


def normalize_text(text: str) -> str:
    """
    Unicode normalization (NFC), cleans whitespace,
    and converts Devanagari numerals.
    """
    if not text:
        return ""
    # Unicode NFC normalization
    normalized = unicodedata.normalize("NFC", text.strip())
    # Convert Devanagari digits
    normalized = convert_devanagari_numerals(normalized)
    # Normalize multiple whitespaces
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized


def extract_matched_entities(text: str) -> Dict[str, Any]:
    """
    Scans the normalized query for domain entities:
    tables, columns, department names, cities, roles, operators, numbers, and aggregations.
    """
    norm_text = normalize_text(text).lower()

    found_tables = set()
    found_columns = set()
    found_departments = set()
    found_cities = set()
    found_roles = set()
    found_aggregations = set()
    found_operators = []
    found_numbers = []

    # 1. Detect Tables
    for tbl, synonyms in TABLE_SYNONYMS.items():
        for syn in synonyms:
            if re.search(r'\b' + re.escape(syn.lower()) + r'\b', norm_text) or (len(syn) > 3 and syn.lower() in norm_text):
                found_tables.add(tbl)
                break

    # 2. Detect Columns
    for col, synonyms in COLUMN_SYNONYMS.items():
        for syn in synonyms:
            if re.search(r'\b' + re.escape(syn.lower()) + r'\b', norm_text) or (len(syn) > 6 and syn.lower() in norm_text):
                found_columns.add(col)
                break

    # 3. Detect Department literals
    for dept_canonical, synonyms in DEPARTMENT_VALUES.items():
        for syn in synonyms:
            if re.search(r'\b' + re.escape(syn.lower()) + r'\b', norm_text) or (len(syn) > 3 and syn.lower() in norm_text):
                found_departments.add(dept_canonical)
                break

    # 4. Detect City literals
    for city_canonical, synonyms in CITY_VALUES.items():
        for syn in synonyms:
            if re.search(r'\b' + re.escape(syn.lower()) + r'\b', norm_text) or (len(syn) > 3 and syn.lower() in norm_text):
                found_cities.add(city_canonical)
                break

    # 5. Detect Role literals
    for role_canonical, synonyms in ROLE_VALUES.items():
        for syn in synonyms:
            if syn.lower() in norm_text:
                found_roles.add(role_canonical)
                break

    # 6. Detect Aggregations
    for agg_type, synonyms in AGGREGATION_PATTERNS:
        for syn in synonyms:
            if syn.lower() in norm_text:
                found_aggregations.add(agg_type)
                break

    # 7. Detect Numbers (numeric digits including decimals e.g., 9.4 or 80000)
    for match in re.finditer(r'\b\d+(?:\.\d+)?\b', norm_text):
        val_str = match.group(0)
        found_numbers.append(float(val_str) if '.' in val_str else int(val_str))

    # Detect written number words if no digits
    if not found_numbers:
        for word, val in WORD_NUMBERS.items():
            if re.search(r'\b' + re.escape(word) + r'\b', norm_text):
                found_numbers.append(val)
                break

    # 8. Detect Operators
    for op, synonyms in OPERATOR_PATTERNS:
        for syn in synonyms:
            if syn.lower() in norm_text:
                found_operators.append(op)
                break

    return {
        "tables": list(found_tables),
        "columns": list(found_columns),
        "departments": list(found_departments),
        "cities": list(found_cities),
        "roles": list(found_roles),
        "aggregations": list(found_aggregations),
        "operators": found_operators,
        "numbers": found_numbers
    }


if __name__ == "__main__":
    import sys
    if sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    samples = [
        "कॉम्प्युटर विभागातील सर्व विद्यार्थी दाखवा",
        "उन कर्मचारियों की सूची दीजिए जिनका वेतन 80000 से अधिक है",
        "पुण्यातील विद्यार्थ्यांची सरासरी gpa किती आहे?",
        "सर्वोच्च पगार असणारा कर्मचारी कोणता?",
        "सिव्हिल विभागाचे प्रमुख कोण आहेत?",
        "how many students in IT department"
    ]
    for s in samples:
        norm = normalize_text(s)
        ent = extract_matched_entities(norm)
        print(f"\nQuery: {s}")
        print(f"Entities: {ent}")
