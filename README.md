# Multilingual Natural Language to SQL Generator

Enter a request in English, Hindi, or Marathi and get a SQL statement. The app does not connect to or execute against a database, and it does not require a sample database or database schema.

## Run

Install dependencies and start the web app:

```powershell
pip install -r requirements.txt
python run.py
```

Open `http://127.0.0.1:8000` in your browser. Enter a request and select **Generate SQL**. Use **Ctrl+Enter** to submit from the text box. Generated SQL can be copied from the result panel.

## Examples

| Language | Request                                                    | SQL output                                                        |
| -------- | ---------------------------------------------------------- | ----------------------------------------------------------------- |
| Marathi  | `कॉम्प्युटर विभागातील सर्व विद्यार्थी दाखवा`               | `SELECT * FROM students WHERE department = 'Computer';`           |
| Hindi    | `उन कर्मचारियों की सूची दीजिए जिनका वेतन 80000 से अधिक है` | `SELECT * FROM employees WHERE salary > 80000;`                   |
| English  | `Show all students with GPA greater than 9.0`              | `SELECT * FROM students WHERE gpa > 9.0;`                         |
| English  | `Add a student named Rahul with ID 101 and age 20`         | `INSERT INTO students (name, id, age) VALUES ('Rahul', 101, 20);` |
| English  | `Change Rahul's age to 21`                                 | `UPDATE students SET age = 21 WHERE name = 'Rahul';`              |
| English  | `Delete the student whose ID is 101`                       | `DELETE FROM students WHERE id = 101;`                            |
| English  | `Find the average age of all students`                     | `SELECT ROUND(AVG(age), 2) AS average_age FROM students;`         |
| Marathi  | `विद्यार्थी नावाचा डेटाबेस तयार करा`                       | `CREATE DATABASE students;`                                       |

The built-in offline language rules recognize the project’s supported academic and employee vocabulary. SQL is returned as text only; the app never runs it.

## Tests

Run the pipeline tests:

```powershell
python -m pytest -q
```

To check the API as well, start the app in one terminal and run:

```powershell
python verify_api.py
```
