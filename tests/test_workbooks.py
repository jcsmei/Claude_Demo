"""Tests for loading the workbooks into the analytical store.

They use the real sample workbooks, which are small, so the numbers
checked here are the ones the assistant will answer with.
"""

import shutil

import duckdb
import openpyxl
import pytest

from assistant import analytics
from assistant import workbooks


@pytest.fixture(scope="module")
def loaded():
    return workbooks.build()


def query(loaded, sql):
    return analytics.run_read_only(loaded.connection, sql)[1]


def test_every_report_loads_with_all_its_tabs(loaded):
    tables = {entry["name"]: entry for entry in loaded.catalog}
    assert tables["paid_social"]["rows"] == 405
    assert tables["site_direct"]["rows"] == 190
    assert tables["site_serve"]["rows"] == 100
    assert tables["creatives"]["rows"] == 695
    assert tables["paid_social"]["tabs"] == [
        "Default Buy", "Facebook Paid", "LINE", "LinkedIn", "Reddit",
        "Twitter Paid", "Xing"]
    assert loaded.warnings == []


def test_every_row_records_its_file_and_tab(loaded):
    rows = query(loaded, "SELECT DISTINCT _source_file, _source_tab "
                         "FROM site_direct ORDER BY 2")
    assert rows == [["site_direct_creatives_2025-10-25.xlsx", "Default Buy"],
                    ["site_direct_creatives_2025-10-25.xlsx", "Display"]]


def test_an_id_shared_by_two_tabs_stays_two_creatives(loaded):
    rows = query(loaded, "SELECT platform, status FROM creatives "
                         "WHERE creative_id = 'CR-LIN-1000' ORDER BY 1")
    assert rows == [["LINE", "Live"], ["LinkedIn", "Not Live"]]


def test_the_view_gives_one_status_column_across_reports(loaded):
    rows = query(loaded, "SELECT status, COUNT(*) FROM creatives "
                         "GROUP BY 1 ORDER BY 1")
    assert rows == [["Live", 269], ["Not Live", 418], ["Unknown", 8]]


def test_a_column_a_report_lacks_is_empty_in_the_view(loaded):
    rows = query(loaded, "SELECT report, COUNT(conversions) FROM creatives "
                         "GROUP BY 1 ORDER BY 1")
    assert rows == [["paid_social", 0], ["site_direct", 0],
                    ["site_serve", 100]]


def test_reddit_counts_match_the_agreed_definitions(loaded):
    rows = query(loaded, "SELECT COUNT(*), COUNT(DISTINCT campaign) "
                         "FROM creatives WHERE platform = 'Reddit' "
                         "AND status = 'Live'")
    assert rows == [[29, 13]]


def test_the_catalog_describes_columns_with_examples(loaded):
    view = loaded.catalog[-1]
    assert view["name"] == "creatives" and view["kind"] == "view"
    status = next(c for c in view["columns"] if c["name"] == "status")
    assert status["type"] == "VARCHAR"
    assert status["examples"] == ["Live", "Not Live", "Unknown"]


def test_the_database_cannot_reach_files_or_be_unlocked(loaded):
    with pytest.raises(duckdb.PermissionException):
        query(loaded, "SELECT * FROM read_csv('requirements.txt')")
    with pytest.raises(duckdb.Error):
        query(loaded, "SET enable_external_access = true")


def test_the_latest_file_of_each_report_is_used(tmp_path):
    source = workbooks.SAMPLE_FOLDER / "site_serve_creatives_2025-10-26.xlsx"
    shutil.copy(source, tmp_path / "site_serve_creatives_2025-09-01.xlsx")
    shutil.copy(source, tmp_path / "site_serve_creatives_2025-10-26.xlsx")
    (tmp_path / "notes.xlsx").write_bytes(b"")
    files = workbooks.latest_files(tmp_path)
    assert files == {
        "site_serve": tmp_path / "site_serve_creatives_2025-10-26.xlsx"}


def test_hidden_empty_or_different_tabs_are_skipped_and_reported(tmp_path):
    book = openpyxl.load_workbook(
        workbooks.SAMPLE_FOLDER / "site_serve_creatives_2025-10-26.xlsx")
    first = book.worksheets[0]
    hidden = book.copy_worksheet(first)
    hidden.title = "Hidden"
    hidden.sheet_state = "hidden"
    book.create_sheet("Empty")
    different = book.create_sheet("Different")
    different.append(["Something", "Else"])
    different.append([1, 2])
    book.save(tmp_path / "site_serve_creatives_2025-11-01.xlsx")

    loaded = workbooks.build(tmp_path)

    assert loaded.catalog[0]["tabs"] == ["All Data"]
    assert loaded.catalog[0]["rows"] == 100
    assert any("'Hidden': hidden" in w for w in loaded.warnings)
    assert any("'Empty': empty" in w for w in loaded.warnings)
    assert any("'Different': columns differ" in w for w in loaded.warnings)
    assert "No Paid Social workbook found" in loaded.warnings


def test_a_tab_missing_needed_columns_is_skipped(tmp_path):
    book = openpyxl.Workbook()
    book.active.title = "Broken"
    book.active.append(["Region", "Channel"])
    book.active.append(["NA", "Display"])
    book.save(tmp_path / "site_direct_creatives_2025-11-01.xlsx")

    loaded = workbooks.build(tmp_path)

    assert loaded.catalog == []
    assert any("'Broken': missing columns" in w for w in loaded.warnings)


def test_run_read_only_keeps_no_changes(loaded):
    analytics.run_read_only(loaded.connection, "DELETE FROM site_serve")
    assert query(loaded, "SELECT COUNT(*) FROM site_serve") == [[100]]


def test_run_read_only_limits_rows_and_time():
    connection = analytics.connect()
    analytics.lock(connection)
    columns, rows = analytics.run_read_only(
        connection, "SELECT * FROM range(500) AS r(x)")
    assert columns == ["x"] and len(rows) == analytics.MAX_ROWS
    with pytest.raises(analytics.QueryTimeout, match="longer than 0.5"):
        analytics.run_read_only(
            connection,
            "WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL "
            "SELECT x + 1 FROM c) SELECT COUNT(*) FROM c",
            seconds=0.5)
