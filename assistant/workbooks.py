"""Load the marketing workbooks into the analytical store.

The latest workbook of each report is read, chosen by the date in its
file name.  Each workbook's tabs share their columns, so they are
stacked into one table, with `_source_file` and `_source_tab` added so
every row can be traced to where it came from.  The view `creatives`
maps the three workbooks' differing column names to one standard set.
The catalog describes it all for the model.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import openpyxl

from assistant import analytics

SAMPLE_FOLDER = Path(__file__).parent.parent / "sample_data"
FILE_PATTERN = re.compile(
    r"^(?P<prefix>.+_)(?P<date>\d{4}-\d{2}-\d{2})\.xlsx$")

# The combined view's columns and their types.  `report` and
# `platform` are added by the view: the platform is the tab.
VIEW_TYPES = {
    "report": "VARCHAR", "platform": "VARCHAR", "region": "VARCHAR",
    "channel": "VARCHAR", "campaign": "VARCHAR",
    "placement_id": "VARCHAR", "creative_name": "VARCHAR",
    "creative_id": "VARCHAR", "status": "VARCHAR",
    "days_since_end": "BIGINT", "impressions": "BIGINT",
    "clicks": "BIGINT", "conversions": "BIGINT", "media_cost": "DOUBLE",
    "account": "VARCHAR", "format": "VARCHAR", "device": "VARCHAR",
}
SHARED = {
    "region": "region", "channel": "channel", "campaign": "campaign_name",
    "placement_id": "placement_id", "creative_name": "creative_name",
    "impressions": "impressions", "clicks": "clicks",
    "media_cost": "media_cost", "account": "account", "format": "format",
    "device": "device",
}


@dataclass(frozen=True)
class Report:
    """One kind of workbook, and how its columns map to the view."""

    name: str              # also the table's name
    prefix: str            # the file name before the date
    title: str             # as people say it
    view_columns: dict     # view column -> this report's column, or None


REPORTS = (
    Report("paid_social", "paid_social_creatives_", "Paid Social", {
        **SHARED, "creative_id": "creative_id",
        "status": "creative_id_status",
        "days_since_end": "days_since_creative_id_end_date",
        "conversions": None,
    }),
    Report("site_direct", "site_direct_creatives_", "Site Direct", {
        **SHARED, "creative_id": None, "status": "creative_status",
        "days_since_end": "days_since_creative_end_date",
        "conversions": None,
    }),
    Report("site_serve", "site_serve_creatives_", "Site Serve", {
        **SHARED, "creative_id": "creative_uid",
        "status": "creative_uid_status",
        "days_since_end": "days_since_uid_end_date",
        "conversions": "total_conversions",
    }),
)


@dataclass
class Workbooks:
    """The locked database, its catalog, and what was skipped."""

    connection: object
    catalog: list
    warnings: list = field(default_factory=list)


def column_name(header):
    """Return a header as a plain SQL name: "Creative ID" -> creative_id."""
    return re.sub(r"[^0-9a-z]+", "_", str(header).lower()).strip("_")


def latest_files(folder):
    """Return the latest workbook of each report, by the date in its name."""
    latest = {}
    for path in folder.glob("*.xlsx"):
        match = FILE_PATTERN.match(path.name)
        if not match or path.name.startswith("~$"):
            continue
        for report in REPORTS:
            if match["prefix"] == report.prefix:
                current = latest.get(report.name)
                if current is None or path.name > current.name:
                    latest[report.name] = path
    return latest


def read_tabs(path, required, warnings):
    """Return the header and rows of each usable tab in a workbook.

    Values are read, never formulas, and nothing in the file runs.  A
    hidden or empty tab, or one whose columns differ from the first
    usable tab, is skipped and noted in `warnings`.
    """
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    header, tabs = None, []
    try:
        for sheet in workbook.worksheets:
            where = f"{path.name}, tab {sheet.title!r}"
            if sheet.sheet_state != "visible":
                warnings.append(f"{where}: hidden, so skipped")
                continue
            rows = [row for row in sheet.iter_rows(values_only=True)
                    if any(value is not None for value in row)]
            if not rows:
                warnings.append(f"{where}: empty, so skipped")
                continue
            names = [column_name(value) for value in rows[0]]
            if header is None:
                missing = sorted(set(required) - set(names))
                if missing:
                    warnings.append(f"{where}: missing columns "
                                    f"{', '.join(missing)}, so skipped")
                    continue
                header = names
            elif names != header:
                warnings.append(f"{where}: columns differ from the other "
                                "tabs, so skipped")
                continue
            tabs.append((sheet.title, rows[1:]))
    finally:
        workbook.close()
    return header, tabs


def sql_type(values):
    """Return the narrowest SQL type that holds all of `values`."""
    present = [value for value in values if value is not None]
    if present and all(isinstance(value, int)
                       and not isinstance(value, bool) for value in present):
        return "BIGINT"
    if present and all(isinstance(value, (int, float))
                       and not isinstance(value, bool) for value in present):
        return "DOUBLE"
    return "VARCHAR"


def load_report(connection, report, path, warnings):
    """Stack a workbook's tabs into one table; return its rows' count."""
    required = [source for source in report.view_columns.values()
                if source]
    header, tabs = read_tabs(path, required, warnings)
    if not tabs:
        warnings.append(f"{path.name}: no usable tabs, so the "
                        f"{report.title} report is missing")
        return 0
    rows = [list(row) + [path.name, tab]
            for tab, tab_rows in tabs for row in tab_rows]
    names = header + ["_source_file", "_source_tab"]
    types = [sql_type(row[index] for row in rows)
             for index in range(len(names))]
    for index, kind in enumerate(types):
        if kind == "VARCHAR":
            for row in rows:
                if row[index] is not None:
                    row[index] = str(row[index])
    columns = ", ".join(f'"{name}" {kind}'
                        for name, kind in zip(names, types))
    connection.execute(f'CREATE TABLE "{report.name}" ({columns})')
    placeholders = ", ".join("?" for _ in names)
    connection.executemany(
        f'INSERT INTO "{report.name}" VALUES ({placeholders})', rows)
    return len(rows)


def create_view(connection, loaded):
    """Create the view `creatives` over every loaded report."""
    selects = []
    for report in REPORTS:
        if report.name not in loaded:
            continue
        fields = [f"'{report.name}' AS report", "_source_tab AS platform"]
        for column, kind in VIEW_TYPES.items():
            if column in ("report", "platform"):
                continue
            source = report.view_columns[column]
            value = f'"{source}"' if source else "NULL"
            fields.append(f"CAST({value} AS {kind}) AS {column}")
        fields += ["_source_file", "_source_tab"]
        selects.append(f'SELECT {", ".join(fields)} FROM "{report.name}"')
    connection.execute("CREATE VIEW creatives AS "
                       + " UNION ALL ".join(selects))


def describe(connection, name, kind, description):
    """Return one catalog entry: columns, types, examples and size."""
    columns = []
    for column, column_type in connection.execute(
            f'SELECT column_name, data_type FROM information_schema.columns '
            f"WHERE table_name = '{name}' ORDER BY ordinal_position"
    ).fetchall():
        examples = [row[0] for row in connection.execute(
            f'SELECT DISTINCT "{column}" FROM "{name}" '
            f'WHERE "{column}" IS NOT NULL ORDER BY 1 LIMIT 3').fetchall()]
        columns.append({"name": column, "type": column_type,
                        "examples": examples})
    tabs = [row[0] for row in connection.execute(
        f'SELECT DISTINCT _source_tab FROM "{name}" ORDER BY 1').fetchall()]
    files = [row[0] for row in connection.execute(
        f'SELECT DISTINCT _source_file FROM "{name}" ORDER BY 1').fetchall()]
    rows = connection.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
    return {"name": name, "kind": kind, "description": description,
            "rows": rows, "files": files, "tabs": tabs, "columns": columns}


def build(folder=SAMPLE_FOLDER):
    """Load the latest workbooks into a new database, and lock it."""
    connection = analytics.connect()
    warnings, loaded = [], []
    files = latest_files(folder)
    for report in REPORTS:
        path = files.get(report.name)
        if path is None:
            warnings.append(f"No {report.title} workbook found")
        elif load_report(connection, report, path, warnings):
            loaded.append(report.name)
    catalog = []
    if loaded:
        create_view(connection, loaded)
        for report in REPORTS:
            if report.name in loaded:
                catalog.append(describe(
                    connection, report.name, "table",
                    f"The {report.title} report: its tabs stacked, one "
                    "row per creative, with its original columns"))
        catalog.append(describe(
            connection, "creatives", "view",
            "Every report, with one standard set of column names"))
    analytics.lock(connection)
    return Workbooks(connection, catalog, warnings)
