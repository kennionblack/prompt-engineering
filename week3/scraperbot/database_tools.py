"""
Database Tools Module

Provides MySQL database integration and management functionality
for the web scraper system.
"""

import json
import logging
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse
import mysql.connector
from mysql.connector import Error
from tools import ToolBox

# Create a dedicated toolbox for database operations
db_tool_box = ToolBox()


class DatabaseTools:
    def __init__(self, db_connection_string: str):
        """
        Initialize DatabaseTools with MySQL connection parameters.

        Args:
            db_connection_string: MySQL connection string in format:
                "mysql://username:password@host:port/database" or
                "host:port:database:username:password"
        """
        self.connection_params = self._parse_connection_string(db_connection_string)
        self.connection = None

        # Test the connection during initialization
        if not self._test_connection():
            raise ConnectionError(f"Failed to connect to MySQL database: {db_connection_string}")

    def _parse_connection_string(self, connection_string: str) -> dict:
        """Parse connection string into individual parameters."""
        try:
            if connection_string.startswith("mysql://"):
                # Format: mysql://username:password@host:port/database
                parsed = urlparse(connection_string)
                return {
                    "host": parsed.hostname,
                    "port": parsed.port or 3306,
                    "database": parsed.path.lstrip("/"),
                    "user": parsed.username,
                    "password": parsed.password,
                    "charset": "utf8mb4",
                    "collation": "utf8mb4_unicode_ci",
                }
            else:
                # Format: host:port:database:username:password
                parts = connection_string.split(":")
                if len(parts) != 5:
                    raise ValueError(
                        "Connection string must be 'host:port:database:username:password'"
                    )

                return {
                    "host": parts[0],
                    "port": int(parts[1]),
                    "database": parts[2],
                    "user": parts[3],
                    "password": parts[4],
                    "charset": "utf8mb4",
                    "collation": "utf8mb4_unicode_ci",
                }
        except Exception as e:
            raise ValueError(f"Invalid connection string format: {e}")

    def _test_connection(self) -> bool:
        """Test the database connection."""
        try:
            connection = self.get_connection()
            if connection and connection.is_connected():
                connection.close()
                return True
            return False
        except Exception:
            return False

    def get_connection(self):
        """
        Get a MySQL database connection.

        Returns:
            mysql.connector.connection: Active MySQL connection
        """
        try:
            connection = mysql.connector.connect(**self.connection_params)

            if connection.is_connected():
                return connection
            else:
                raise ConnectionError("Failed to establish database connection")

        except ImportError:
            raise ImportError(
                "mysql-connector-python not installed. Run: pip install mysql-connector-python"
            )
        except Error as e:
            raise ConnectionError(f"MySQL connection error: {e}")
        except Exception as e:
            raise ConnectionError(f"Unexpected database connection error: {e}")

    @db_tool_box.tool
    def execute_query(self, query: str, params: Optional[dict] = None) -> dict:
        """
        Execute a SQL query and return results.

        Args:
            query: SQL query string
            params: Optional dictionary of parameters for parameterized queries

        Returns:
            dict: Query results with columns and rows
        """
        connection = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor(dictionary=True)

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Handle SELECT queries
            if query.strip().upper().startswith("SELECT"):
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                return {
                    "success": True,
                    "columns": columns,
                    "rows": results,
                    "row_count": len(results),
                }
            else:
                # Handle INSERT, UPDATE, DELETE, etc.
                connection.commit()
                return {
                    "success": True,
                    "affected_rows": cursor.rowcount,
                    "message": f"Query executed successfully. {cursor.rowcount} rows affected.",
                }

        except Exception as e:
            if connection:
                connection.rollback()
            return {"success": False, "error": str(e), "message": f"Query execution failed: {e}"}
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()

    @db_tool_box.tool
    def get_database_schema(self) -> dict:
        """
        Get the complete database schema with sample data from each table.

        Returns:
            dict: Database schema with table structures and sample data
        """
        try:
            # Get all table names
            tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = %s
            """

            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.execute(tables_query, (self.connection_params["database"],))
            table_names = [row[0] for row in cursor.fetchall()]

            schema = {"database": self.connection_params["database"], "tables": []}

            # Get schema and sample data for each table
            for table_name in table_names:
                table_info = {"name": table_name, "columns": [], "sample_rows": []}

                # Get column information
                columns_query = """
                SELECT column_name, data_type, is_nullable, column_default, column_key
                FROM information_schema.columns 
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
                """
                cursor.execute(columns_query, (self.connection_params["database"], table_name))
                columns = cursor.fetchall()

                for col in columns:
                    table_info["columns"].append(
                        {
                            "name": col[0],
                            "type": col[1],
                            "nullable": col[2] == "YES",
                            "default": col[3],
                            "key": col[4],
                        }
                    )

                # Get sample data (first 3 rows)
                try:
                    sample_query = f"SELECT * FROM `{table_name}` LIMIT 3"
                    cursor.execute(sample_query)
                    sample_results = cursor.fetchall()

                    # Convert rows to dictionaries
                    column_names = [col["name"] for col in table_info["columns"]]
                    for row in sample_results:
                        row_dict = dict(zip(column_names, row))
                        table_info["sample_rows"].append(row_dict)

                except Exception as e:
                    table_info["sample_rows"] = []
                    table_info["sample_error"] = str(e)

                schema["tables"].append(table_info)

            cursor.close()
            connection.close()

            return {"success": True, "schema": schema}

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to retrieve database schema: {e}",
            }

    @db_tool_box.tool
    def create_table_from_data(self, table_name: str, sample_data: list) -> dict:
        """
        Create a table based on sample data structure.

        Args:
            table_name: Name for the new table
            sample_data: List of dictionaries representing sample rows

        Returns:
            dict: Result of table creation
        """
        if not sample_data:
            return {"success": False, "error": "No sample data provided"}

        try:
            # Analyze sample data to determine column types
            columns = {}
            for row in sample_data:
                for key, value in row.items():
                    if key not in columns:
                        columns[key] = self._infer_column_type(value)
                    else:
                        # Update type if we find a more specific type
                        current_type = self._infer_column_type(value)
                        if current_type != columns[key]:
                            columns[key] = self._resolve_type_conflict(columns[key], current_type)

            # Build CREATE TABLE statement
            column_defs = []
            for col_name, col_type in columns.items():
                column_defs.append(f"`{col_name}` {col_type}")

            create_query = f"""
            CREATE TABLE IF NOT EXISTS `{table_name}` (
                id INT AUTO_INCREMENT PRIMARY KEY,
                {', '.join(column_defs)},
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """

            return self.execute_query(create_query)

        except Exception as e:
            return {"success": False, "error": str(e), "message": f"Failed to create table: {e}"}

    def _infer_column_type(self, value) -> str:
        """Infer MySQL column type from Python value."""
        if value is None:
            return "TEXT"
        elif isinstance(value, bool):
            return "BOOLEAN"
        elif isinstance(value, int):
            return "BIGINT"
        elif isinstance(value, float):
            return "DECIMAL(10,2)"
        elif isinstance(value, str):
            if len(value) <= 255:
                return "VARCHAR(255)"
            elif len(value) <= 65535:
                return "TEXT"
            else:
                return "LONGTEXT"
        else:
            return "JSON"

    def _resolve_type_conflict(self, type1: str, type2: str) -> str:
        """Resolve conflicts between inferred types by choosing the more general type."""
        # Priority: JSON > LONGTEXT > TEXT > VARCHAR > DECIMAL > BIGINT > BOOLEAN
        type_priority = {
            "BOOLEAN": 1,
            "BIGINT": 2,
            "DECIMAL(10,2)": 3,
            "VARCHAR(255)": 4,
            "TEXT": 5,
            "LONGTEXT": 6,
            "JSON": 7,
        }

        priority1 = type_priority.get(type1, 0)
        priority2 = type_priority.get(type2, 0)

        return type1 if priority1 >= priority2 else type2


# TODOS: add validate_sql tool? tbh it's easier just to run a query and see if it fails
# add a tool that can set up a database
# and separate tool that can run queries against that database

"""
Database Schema Analysis Notes:

So we can get a list of the first three results in each database table with this query:

SELECT CONCAT('SELECT DISTINCT * FROM ', table_name, ' LIMIT 3;')
FROM information_schema.tables
WHERE table_schema = 'your_database_name';

then we can run each of these queries in a list (parallelized if we're feeling fancy) 
and get a sample of the data in each table.

we then programatically turn this into a json object that has an array of tables, 
each with a name and an array of rows (each row is a json object with column names as keys).

This would look like the following:
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
