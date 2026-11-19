"""The two pages under Manage, and their read tools."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from meridian.suites import Recorder
from meridian.testing import PageClient

from norges_bank import page as page_module
from norges_bank.page import CONNECTION, DATASETS_PAGE, figures, hold, pages

from conftest import HELD, INSTANCE, feed, resolving


@pytest.fixture
def client(tmp_path: Path) -> PageClient:
    work = feed(tmp_path, resolving(Recorder(INSTANCE), "Zero coupon yields"))
    asyncio.run(work.check())
    hold(work)
    return PageClient(pages)


def test_each_page_is_managed_alone(client: PageClient) -> None:
    served = {(r.page.path, r.level): r.response.status for r in client.every_page()}
    assert served == {
        (CONNECTION, "admin"): 200,
        (CONNECTION, "write"): 403,
        (CONNECTION, "read"): 403,
        (DATASETS_PAGE, "admin"): 200,
        (DATASETS_PAGE, "write"): 403,
        (DATASETS_PAGE, "read"): 403,
    }
    client.assert_no_account_data("9.6866", "119.47921710", "4.343")


def test_connection_and_its_sources(client: PageClient) -> None:
    text = client.get(CONNECTION, "admin").text
    assert "No key needed" in text and "Does not stream" in text and "1 record not held" in text
    sources = client.get(CONNECTION, "admin", tab="sources").text
    assert sources.count("<tr data-source=") == 5
    assert "Thu 19 Nov 2026" in sources and "Wed 18 Nov 2026" in sources


def test_datasets_and_records(client: PageClient) -> None:
    text = client.get(DATASETS_PAGE, "admin").text
    keys = ("norgesbank_rates", "norgesbank_curves", "norgesbank_fx")
    assert all(f"norges-bank:{k}" in text for k in keys)
    records = client.get(DATASETS_PAGE, "admin", tab="records").text
    assert 'data-code="NOWA"' in records and 'data-code="USD"' in records
    assert 'data-code="XDR"' in records and "Source: Norges Bank" in records
    searched = client.get(DATASETS_PAGE, "admin", q="NOWA").text
    assert searched.count("<tr data-code=") >= 2


def test_the_tools_answer_what_the_pages_show(client: PageClient) -> None:
    data = client.call_tool("read_connection").data
    assert data["mode"] == "Sample data" and [s["dataset"] for s in data["sources"]] == [
        "norges-bank:norgesbank_rates", "norges-bank:norgesbank_rates",
        "norges-bank:norgesbank_curves", "norges-bank:norgesbank_curves",
        "norges-bank:norgesbank_fx",
    ]  # fmt: skip
    read = client.call_tool("read_datasets").data
    held = {r["code"]: r for r in read["records"]}
    assert held["NOWA"]["instrument_id"] == HELD["NOWA"]
    assert held["Zero coupon yields"]["miss"] == "not held: reported missing"
    assert held["USD"]["instrument_id"] == "LCL-USD" and held["USD"]["name"] == "US dollar"
    assert held["USD"]["latest_day"] == "2026-11-19"
    assert held["XDR"]["miss"] == "not carried"


def test_before_the_first_check_and_not_reached(tmp_path: Path) -> None:
    page_module._held.clear()
    assert "Checking Norges Bank" in PageClient(pages).get(CONNECTION, "admin").text
    work = feed(tmp_path)
    work.status.sources["nowa"].error = "https://data.norges-bank.no/api: URLError"
    hold(work)
    text = PageClient(pages).get(CONNECTION, "admin").text
    assert 'state="error"' in text and "Not answering" in text


def test_the_figures_are_the_data_roles(client: PageClient) -> None:
    work = page_module._held["feed"]
    said = figures(work.status, work)
    assert [f.label for f in said][:3] == ["Connection", "Entitled at the vendor", "Stream"]
