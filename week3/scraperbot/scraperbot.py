from pathlib import Path


def replace_keyword(original_text: str, keyword: str, replacement: str) -> str:
    """Replaces all occurrences of ${keyword} in original_text with replacement."""
    return original_text.replace(f"${{{keyword}}}", replacement)


def replace_keywords(original_text: str, replacements: dict[str, str]) -> str:
    """Replaces all occurrences of ${keyword} in original_text with replacement for each key, value pair in replacements."""
    for key, value in replacements.items():
        original_text = replace_keyword(original_text, key, value)
    return original_text


def populate_prompt(prompt_path: Path, replacements: dict[str, str]) -> str:
    """Reads the prompt file at prompt_path and replaces all occurrences of ${keyword} in the prompt with replacement for each key, value pair in replacements."""
    try:
        prompt_text = Path(prompt_path).read_text()
        return replace_keywords(prompt_text, replacements)
    except FileNotFoundError:
        print(f"File ${prompt_path} does not exist at the specified location")
        return ""


# TODOS: add validate_sql tool? tbh it's easier just to run a query and see if it fails
# add a tool that can set up a database
# and separate tool that can run queries against that database

"""
So we can get a list of the first three results in each database table with this query:

SELECT CONCAT('SELECT DISTINCT * FROM ', table_name, ' LIMIT 3;')
FROM information_schema.tables
WHERE table_schema = 'your_database_name';

then we can run each of these queries in a list (parallelized if we're feeling fancy) and get a sample of the data in each table.
we then programatically turn this into a json object that has an array of tables, each with a name and an array of rows (each row is a json object with column names as keys).
this would look like the following:
{
    "tables": [
        {
            "name": "table1",
            "rows": [
                {"column1": "value1", "column2": "value2", ...},
                {"column1": "value1", "column2": "value2", ...},
                {"column1": "value1", "column2": "value2", ...}
            ]
        },
        {
            "name": "table2",
            "rows": [
                {"column1": "value1", "column2": "value2", ...},
                {"column1": "value1", "column2": "value2", ...},
                {"column1": "value1", "column2": "value2", ...}
            ]
        },
        ...
    ]
}
I think we can pass this object straight into the prompt but I'm not sold on that yet. Test and see
"""
