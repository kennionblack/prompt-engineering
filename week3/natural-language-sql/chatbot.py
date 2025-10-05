from openai import OpenAI
import os
import mysql.connector
from pathlib import Path
from prompt_utils import PromptTextInsertion
from dotenv import load_dotenv

load_dotenv()


fdir = os.path.dirname(__file__)


initialize_sql_path = os.path.join(fdir, "initialize.sql")
populate_sql_path = os.path.join(fdir, "populate.sql")


DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3307")),
    "user": os.getenv("DB_USER", "chatbot_user"),
    "password": os.getenv("DB_PASSWORD", "chatbot_pass"),
    "database": os.getenv("DB_NAME", "chatbot_db"),
}


try:
    mysqlCon = mysql.connector.connect(**DB_CONFIG)
    mysqlCursor = mysqlCon.cursor()
except mysql.connector.Error as err:
    print(f"Error connecting to MySQL database: {err}")
    print("Make sure the MySQL container is running: docker-compose up -d")
    exit(1)

with open(initialize_sql_path) as initializeSqlFile, open(populate_sql_path) as populateSqlFile:
    initializeSqlScript = initializeSqlFile.read()
    populateSqlScript = populateSqlFile.read()


def runSql(query):
    try:
        mysqlCursor.execute(query)
        result = mysqlCursor.fetchall()
        return result
    except mysql.connector.Error as err:
        print(f"SQL Error: {err}")
        raise err


openAiClient = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def getChatGptResponse(content):
    stream = openAiClient.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": content}],
        stream=True,
    )

    responseList = []
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            responseList.append(chunk.choices[0].delta.content)

    result = "".join(responseList)
    return result


strategies = {
    "zero_shot": "zero_shot_sql",
    "few_shot": "few_shot_sql",
}

questions = [
    "Which books have been checked out most frequently?",
    "What are the most popular genres in our library?",
    "Which books are currently missing from the audit?",
    "What books are available at the Lehi campus?",
    "Which authors have the most books in our collection?",
    "What books have never been checked out?",
    "Which campus has more inventory?",
]


def sanitizeForJustSql(value):
    gptStartSqlMarker = "```sql"
    gptEndSqlMarker = "```"
    if gptStartSqlMarker in value:
        value = value.split(gptStartSqlMarker)[1]
    if gptEndSqlMarker in value:
        value = value.split(gptEndSqlMarker)[0]

    return value


for strategy in strategies:
    print("########################################################################")
    print(f"Running strategy: {strategy}")
    print("########################################################################")

    for question in questions:
        print("\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        print(f"Question: {question}")
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

        try:
            # Generate SQL using the appropriate strategy prompt
            sql_prompt_path = Path(fdir) / "prompts" / f"{strategies[strategy]}.md"
            getSqlFromQuestionEngineeredPrompt = PromptTextInsertion.populate_prompt(
                sql_prompt_path,
                {
                    "SCHEMA": initializeSqlScript,
                    "QUESTION": question,
                },
            )

            sqlSyntaxResponse = getChatGptResponse(getSqlFromQuestionEngineeredPrompt)
            sqlSyntaxResponse = sanitizeForJustSql(sqlSyntaxResponse)
            print(f"\nSQL Query:\n{sqlSyntaxResponse}")

            queryRawResponse = str(runSql(sqlSyntaxResponse))
            print(f"\nRaw Results:\n{queryRawResponse}")

            # Generate friendly response with full context
            friendly_prompt_path = Path(fdir) / "prompts" / "friendly_response.md"
            friendlyResultsPrompt = PromptTextInsertion.populate_prompt(
                friendly_prompt_path,
                {
                    "SCHEMA": initializeSqlScript,
                    "QUESTION": question,
                    "SQL_QUERY": sqlSyntaxResponse,
                    "QUERY_RESULT": queryRawResponse,
                },
            )

            friendlyResponse = getChatGptResponse(friendlyResultsPrompt)
            print(f"\nFriendly Answer:\n{friendlyResponse}")

        except Exception as err:
            print(f"\nError: {err}")

    print("\n")


mysqlCursor.close()
mysqlCon.close()
print("Done!")
