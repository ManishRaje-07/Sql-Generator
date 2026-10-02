"""Verify that multilingual API requests return SQL without execution."""

import os
import requests

BASE_URL = os.environ.get("SQL_GENERATOR_URL", "http://127.0.0.1:8000")

home = requests.get(BASE_URL)
assert home.status_code == 200
assert "Natural Language to SQL Generator" in home.text

queries = [
    ("कॉम्प्युटर विभागातील सर्व विद्यार्थी दाखवा", "department = 'Computer'"),
    ("उन कर्मचारियों की सूची दीजिए जिनका वेतन 80000 से अधिक है", "salary > 80000"),
    ("Show all students with GPA greater than 9.0", "gpa > 9"),
    ("विद्यार्थी नावाचा डेटाबेस तयार करा", "CREATE DATABASE students;"),
    ("Add a student named Rahul with ID 101 and age 20.", "INSERT INTO students (name, id, age) VALUES ('Rahul', 101, 20);"),
    ("101 आईडी और उम्र 20 के साथ राहुल नाम का छात्र जोड़ें", "INSERT INTO students (name, id, age) VALUES ('राहुल', 101, 20);"),
    ("१०१ आयडी आणि वय २० असलेला राहुल नावाचा विद्यार्थी जोडा", "INSERT INTO students (name, id, age) VALUES ('राहुल', 101, 20);"),
        ("Change Rahul's age to 21.", "UPDATE students SET age = 21 WHERE name = 'Rahul';"), 
        ("Delete the student whose ID is 101", "DELETE FROM students WHERE id = 101;"),
        ("ज्याचा ID 101 आहे तो विद्यार्थी हटवा.", "DELETE FROM students WHERE id = 101;"),
        ("Rahul की उम्र 21 कर दें.", "UPDATE students SET age = 21 WHERE name = 'Rahul';"),
        ("ID, नाव आणि वय असलेले Students नावाचे टेबल तयार करा", "CREATE TABLE students (id INTEGER, name TEXT, age INTEGER);"),
        ("8 वर्ष से अधिक उम्र वाले विद्यार्थियों को दिखाइए", "WHERE age > 8"),
        ("सर्व विद्यार्थ्यांना वयानुसार उतरत्या क्रमाने दाखवा", "ORDER BY age DESC"),
        ("Count the total number of students.", "COUNT(*)"),
        ("find the average age of all students", "AVG(age)"),
        ("सर्वात जास्त वय असलेल्या विद्यार्थ्यांचे वय शोधा.", "MAX(age)"),
        ("Show students whose age is between 18 and 22", "age >= 18 AND age <= 22"),
        ("Show the top 5 students by GPA", "ORDER BY gpa DESC LIMIT 5"),
    ("18 से 22 वर्ष की उम्र वाले विद्यार्थी दिखाओ", "age >= 18 AND age <= 22"),
    ("18 ते 22 वयाच्या विद्यार्थ्यांना दाखवा", "age >= 18 AND age <= 22"),
    ("शीर्ष 5 छात्रों को GPA के आधार पर दिखाओ", "ORDER BY gpa DESC LIMIT 5"),
    ("सर्वात वरचे 5 विद्यार्थी GPA नुसार दाखवा", "ORDER BY gpa DESC LIMIT 5"),
        ("Delete all students whose GPA is below 5", "DELETE FROM students WHERE gpa < 5;"),
]

for query, expected_sql in queries:
    response = requests.post(
        f"{BASE_URL}/api/query",
        json={"query": query, "language": "auto"},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["success"], result
    assert expected_sql in result["sql"]["query"]
    assert "execution" not in result
    print(f"{query} -> {result['sql']['query']}")

print("All SQL-only API checks passed.")
