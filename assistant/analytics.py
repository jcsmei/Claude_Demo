"""The analytical store: DuckDB, in memory, locked before queries run.

DuckDB's SQL can read files and reach the network.  `lock` switches
both off and locks the configuration, so no later statement can switch
them back on.  `run_read_only` runs each query inside a transaction
that is always rolled back, so nothing it changes is kept; it returns
at most `MAX_ROWS` rows and stops a query that runs longer than
`MAX_QUERY_SECONDS`.
"""

import threading

import duckdb

MAX_ROWS = 50
MAX_QUERY_SECONDS = 5


class QueryTimeout(Exception):
    """A query ran longer than `MAX_QUERY_SECONDS` and was stopped."""


def connect():
    """Return a new, empty in-memory database."""
    return duckdb.connect(":memory:")


def lock(connection):
    """Stop SQL from reaching files or the network, for good."""
    connection.execute("SET enable_external_access = false")
    connection.execute("SET lock_configuration = true")


def run_read_only(connection, statement, max_rows=MAX_ROWS, seconds=None):
    """Run `statement` and return its column names and first rows.

    Each call gets its own cursor, so one shared database can serve
    several visitors at once.  The statement runs inside a transaction
    that is rolled back afterwards, so any change it makes is undone.
    A query still running after `seconds`, by default
    `MAX_QUERY_SECONDS`, is interrupted and raises `QueryTimeout`.  Any
    other SQL error is raised as DuckDB raises it.
    """
    seconds = seconds or MAX_QUERY_SECONDS
    cursor = connection.cursor()
    cursor.execute("BEGIN TRANSACTION")
    timer = threading.Timer(seconds, cursor.interrupt)
    timer.start()
    try:
        result = cursor.execute(statement)
        columns = [column[0] for column in result.description]
        rows = [list(row) for row in result.fetchmany(max_rows)]
    except duckdb.InterruptException as error:
        raise QueryTimeout(
            f"The query ran longer than {seconds} seconds and was stopped."
        ) from error
    finally:
        timer.cancel()
        cursor.execute("ROLLBACK")
        cursor.close()
    return columns, rows
