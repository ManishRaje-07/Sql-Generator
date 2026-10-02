"""
Comprehensive Test Suite for Multilingual NL-to-SQL Generator.
Tests multilingual SQL generation without database access.
"""

import sys
import unittest

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from pipeline import process_query_pipeline
from nlp.validator import validate_sql_safety


class TestMultilingualNLtoSQL(unittest.TestCase):

    def test_marathi_students_department(self):
        query = "कॉम्प्युटर विभागातील सर्व विद्यार्थी दाखवा"
        res = process_query_pipeline(query)
        self.assertTrue(res["success"])
        self.assertEqual(res["language"]["code"], "mr")
        self.assertEqual(res["intent"]["target_table"], "students")
        self.assertIn("department = 'Computer'", res["sql"]["query"])

    def test_hindi_employees_salary_filter(self):
        query = "उन कर्मचारियों की सूची दीजिए जिनका वेतन 80000 से अधिक है"
        res = process_query_pipeline(query)
        self.assertTrue(res["success"])
        self.assertEqual(res["language"]["code"], "hi")
        self.assertEqual(res["intent"]["target_table"], "employees")
        self.assertIn("salary > 80000", res["sql"]["query"])

    def test_marathi_avg_gpa_city(self):
        query = "पुण्यातील विद्यार्थ्यांची सरासरी gpa किती आहे?"
        res = process_query_pipeline(query)
        self.assertTrue(res["success"])
        self.assertEqual(res["language"]["code"], "mr")
        self.assertEqual(res["intent"]["target_table"], "students")
        self.assertIn("AVG(gpa)", res["sql"]["query"])
        self.assertIn("city = 'Pune'", res["sql"]["query"])

    def test_hindi_age_filter_uses_age_column(self):
        res = process_query_pipeline("8 वर्ष से अधिक उम्र वाले विद्यार्थियों को दिखाइए")
        self.assertTrue(res["success"])
        self.assertIn("WHERE age > 8", res["sql"]["query"])

    def test_age_between_filter_keeps_both_bounds(self):
        queries = [
            "Show students whose age is between 18 and 22",
            "18 से 22 वर्ष की उम्र वाले विद्यार्थी दिखाओ",
            "18 ते 22 वयाच्या विद्यार्थ्यांना दाखवा"
        ]
        for query in queries:
            with self.subTest(query=query):
                res = process_query_pipeline(query)
                self.assertTrue(res["success"])
                self.assertIn("WHERE age >= 18 AND age <= 22", res["sql"]["query"])
                self.assertNotIn("year_of_study", res["sql"]["query"])

    def test_top_n_orders_and_limits_instead_of_aggregating(self):
        queries = [
            "Show the top 5 students by GPA",
            "शीर्ष 5 छात्रों को GPA के आधार पर दिखाओ",
            "सर्वात वरचे 5 विद्यार्थी GPA नुसार दाखवा"
        ]
        for query in queries:
            with self.subTest(query=query):
                res = process_query_pipeline(query)
                self.assertTrue(res["success"])
                self.assertEqual(
                    res["sql"]["query"],
                    "SELECT * FROM students ORDER BY gpa DESC LIMIT 5;"
                )

    def test_marathi_age_sort_uses_descending_order(self):
        res = process_query_pipeline("सर्व विद्यार्थ्यांना वयानुसार उतरत्या क्रमाने दाखवा")
        self.assertTrue(res["success"])
        self.assertEqual(res["sql"]["query"], "SELECT * FROM students ORDER BY age DESC;")

    def test_total_number_uses_count_not_sum(self):
        res = process_query_pipeline("Count the total number of students.")
        self.assertTrue(res["success"])
        self.assertEqual(res["sql"]["query"], "SELECT COUNT(*) AS total_count FROM students;")

    def test_total_salary_still_uses_sum(self):
        res = process_query_pipeline("Find the total salary of employees.")
        self.assertTrue(res["success"])
        self.assertIn("SUM(salary)", res["sql"]["query"])

    def test_average_age_uses_age_column(self):
        res = process_query_pipeline("find the average age of all students")
        self.assertTrue(res["success"])
        self.assertEqual(
            res["sql"]["query"],
            "SELECT ROUND(AVG(age), 2) AS average_age FROM students;"
        )

    def test_marathi_highest_age_uses_age_column(self):
        res = process_query_pipeline("सर्वात जास्त वय असलेल्या विद्यार्थ्यांचे वय शोधा.")
        self.assertTrue(res["success"])
        self.assertEqual(res["sql"]["query"], "SELECT MAX(age) AS max_age FROM students;")

    def test_marathi_superlative_salary(self):
        query = "सर्वोच्च पगार असणारा कर्मचारी कोणता?"
        res = process_query_pipeline(query)
        self.assertTrue(res["success"])
        self.assertEqual(res["language"]["code"], "mr")
        self.assertEqual(res["intent"]["target_table"], "employees")
        self.assertIn("ORDER BY salary DESC LIMIT 1", res["sql"]["query"])

    def test_english_query(self):
        query = "Show all students from Computer department"
        res = process_query_pipeline(query)
        self.assertTrue(res["success"])
        self.assertEqual(res["language"]["code"], "en")
        self.assertEqual(res["intent"]["target_table"], "students")
        self.assertIn("department = 'Computer'", res["sql"]["query"])

    def test_add_student_generates_insert_instead_of_select(self):
        queries = [
            (
                "Add a student named Rahul with ID 101 and age 20.",
                "INSERT INTO students (name, id, age) VALUES ('Rahul', 101, 20);"
            ),
            (
                "101 आईडी और उम्र 20 के साथ राहुल नाम का छात्र जोड़ें",
                "INSERT INTO students (name, id, age) VALUES ('राहुल', 101, 20);"
            ),
            (
                "१०१ आयडी आणि वय २० असलेला राहुल नावाचा विद्यार्थी जोडा",
                "INSERT INTO students (name, id, age) VALUES ('राहुल', 101, 20);"
            )
        ]
        for query, expected_sql in queries:
            with self.subTest(query=query):
                res = process_query_pipeline(query)
                self.assertTrue(res["success"])
                self.assertEqual(res["sql"]["query"], expected_sql)
                self.assertNotIn("execution", res)

    def test_supported_sql_intent_matrix(self):
        cases = [
            (
                "Show students with age greater than 18",
                "SELECT name, age FROM students WHERE age > 18;"
            ),
            (
                "Show students in descending order by GPA",
                "SELECT name, gpa FROM students ORDER BY gpa DESC;"
            ),
            (
                "Show students in ascending order by name",
                "SELECT name FROM students ORDER BY name ASC;"
            ),
            (
                "Show top 5 employees by salary",
                "SELECT * FROM employees ORDER BY salary DESC LIMIT 5;"
            ),
            (
                "Count employees in IT department",
                "SELECT COUNT(*) AS total_count FROM employees WHERE department = 'IT';"
            ),
            (
                "Find the total budget of departments",
                "SELECT SUM(budget) AS total_budget FROM departments;"
            ),
            (
                "Update the age of student with ID 101 to 22",
                "UPDATE students SET age = 22 WHERE id = 101;"
            ),
            (
                "Delete all students whose GPA is below 5",
                "DELETE FROM students WHERE gpa < 5;"
            )
        ]
        for query, expected_sql in cases:
            with self.subTest(query=query):
                result = process_query_pipeline(query)
                self.assertTrue(result["success"], result.get("error"))
                self.assertEqual(result["sql"]["query"], expected_sql)
                self.assertNotIn("execution", result)

    def test_update_student_generates_filtered_update(self):
        res = process_query_pipeline("Change Rahul's age to 21.")
        self.assertTrue(res["success"])
        self.assertEqual(
            res["sql"]["query"],
            "UPDATE students SET age = 21 WHERE name = 'Rahul';"
        )
        self.assertNotIn("execution", res)

    def test_delete_student_generates_filtered_delete(self):
        res = process_query_pipeline("Delete the student whose ID is 101")
        self.assertTrue(res["success"])
        self.assertEqual(res["sql"]["query"], "DELETE FROM students WHERE id = 101;")
        self.assertNotIn("execution", res)

    def test_delete_with_numeric_condition_generates_filtered_delete(self):
        res = process_query_pipeline("Delete all students whose GPA is below 5")
        self.assertTrue(res["success"])
        self.assertEqual(res["sql"]["query"], "DELETE FROM students WHERE gpa < 5;")

    def test_mutations_without_row_conditions_are_rejected(self):
        update = process_query_pipeline("Change the student's age to 21")
        delete = process_query_pipeline("Delete all students")
        self.assertFalse(update["success"])
        self.assertFalse(delete["success"])

    def test_screenshot_marathi_delete_prompt(self):
        res = process_query_pipeline("ज्याचा ID 101 आहे तो विद्यार्थी हटवा.")
        self.assertTrue(res["success"])
        self.assertEqual(res["sql"]["query"], "DELETE FROM students WHERE id = 101;")

    def test_screenshot_hindi_update_prompt(self):
        res = process_query_pipeline("Rahul की उम्र 21 कर दें.")
        self.assertTrue(res["success"])
        self.assertEqual(
            res["sql"]["query"],
            "UPDATE students SET age = 21 WHERE name = 'Rahul';"
        )

    def test_screenshot_marathi_create_table_prompt(self):
        res = process_query_pipeline("ID, नाव आणि वय असलेले Students नावाचे टेबल तयार करा")
        self.assertTrue(res["success"])
        self.assertEqual(
            res["sql"]["query"],
            "CREATE TABLE students (id INTEGER, name TEXT, age INTEGER);"
        )

    def test_departments_hod(self):
        query = "सिव्हिल विभागाचे प्रमुख कोण आहेत?"
        res = process_query_pipeline(query)
        self.assertTrue(res["success"])
        self.assertEqual(res["intent"]["target_table"], "departments")
        self.assertIn("name = 'Civil'", res["sql"]["query"])

    def test_count_students_it(self):
        query = "आयटी विभागात किती विद्यार्थी आहेत?"
        res = process_query_pipeline(query)
        self.assertTrue(res["success"])
        self.assertEqual(res["intent"]["target_table"], "students")
        self.assertIn("COUNT(*)", res["sql"]["query"])
        self.assertIn("department = 'IT'", res["sql"]["query"])

    def test_database_creation_returns_sql_only_in_supported_languages(self):
        queries = [
            ("विद्यार्थी नावाचा डेटाबेस तयार करा", "CREATE DATABASE students;"),
            ("छात्रों के लिए डेटाबेस बनाओ", "CREATE DATABASE students;"),
            ("Create database inventory", "CREATE DATABASE inventory;")
        ]
        for query, expected_sql in queries:
            with self.subTest(query=query):
                res = process_query_pipeline(query)
                self.assertTrue(res["success"])
                self.assertEqual(res["sql"]["query"], expected_sql)
                self.assertNotIn("execution", res)

    def test_sql_safety_blocks_destructive(self):
        res1 = validate_sql_safety("DROP TABLE students;")
        self.assertFalse(res1["is_safe"])

        res2 = validate_sql_safety("DELETE FROM employees;")
        self.assertFalse(res2["is_safe"])

        res3 = validate_sql_safety("SELECT * FROM students; DROP TABLE departments;")
        self.assertFalse(res3["is_safe"])


if __name__ == "__main__":
    unittest.main()
