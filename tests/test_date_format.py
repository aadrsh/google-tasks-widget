import pytest
from datetime import date, timedelta
from main import format_due_date

def test_format_due_date_none():
    label, color = format_due_date(None)
    assert label is None
    assert color is None

def test_format_due_date_none_with_recurrence():
    label, color = format_due_date(None, recurrence=["RRULE:FREQ=DAILY"])
    assert label == "🔁"
    assert color == "#888888"

def test_format_due_date_today():
    today_str = date.today().strftime("%Y-%m-%d") + "T00:00:00.000Z"
    label, color = format_due_date(today_str)
    assert "Today" in label
    assert color == "#4da8da"

def test_format_due_date_tomorrow():
    tomorrow_str = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d") + "T00:00:00.000Z"
    label, color = format_due_date(tomorrow_str)
    assert "Tomorrow" in label
    assert color == "#a8e6cf"

def test_format_due_date_yesterday():
    yesterday_str = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d") + "T00:00:00.000Z"
    label, color = format_due_date(yesterday_str)
    assert "Yesterday" in label
    assert color == "#ff6b6b"

def test_format_due_date_overdue():
    overdue_str = (date.today() - timedelta(days=5)).strftime("%Y-%m-%d") + "T00:00:00.000Z"
    label, color = format_due_date(overdue_str)
    assert "Overdue" in label
    assert color == "#ff6b6b"

def test_format_due_date_recurrence_suffix():
    today_str = date.today().strftime("%Y-%m-%d") + "T00:00:00.000Z"
    label, color = format_due_date(today_str, recurrence=["RRULE:FREQ=DAILY"])
    assert "🔁" in label
