"""The plugin's own conversion of Norges Bank's recorded answers."""

from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path

from meridian.operations import as_decimal
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.suites import Recorder

from norges_bank.portal import NO_DATA, SyntheticPortal, path_for, within
from norges_bank.sdmx import FX_FLOW, NotRead, parse

from conftest import CURVES, FX, HELD, INSTANCE, feed, resolving, want


def checked(tmp: Path, *left_out: str) -> Recorder:
    plugin = resolving(Recorder(INSTANCE), *left_out)
    asyncio.run(feed(tmp, plugin).check())
    return plugin


def rates_of(plugin: Recorder, subject: str) -> list[ops.Rate]:
    return [
        r
        for b in plugin.on("RecordRates")
        for r in b.rates
        if r.meta.subjects[0].entity_id == subject
    ]


def test_nowa_a_fixing_act_365_with_its_transactions(tmp_path: Path) -> None:
    nowa = rates_of(checked(tmp_path), HELD["NOWA"])
    day = next(r for r in nowa if r.meta.business_date == "2026-11-18")
    assert day.kind == ops.RATE_KIND_FIXING and str(as_decimal(day.value.value)) == "4.50"
    assert day.convention.day_count == ops.DAY_COUNT_ACT_365_FIXED
    assert day.convention.compounding == ops.COMPOUNDING_SIMPLE
    assert day.transaction_count == 9 and not day.HasField("volume") and not day.percentiles
    assert not day.meta.source_times and day.meta.raw.key.startswith("responses/")


def test_the_index_and_the_policy_rate(tmp_path: Path) -> None:
    plugin = checked(tmp_path)
    index = {r.meta.business_date: r for r in rates_of(plugin, HELD["NOWA compounded index"])}
    assert index["2026-11-18"].kind == ops.RATE_KIND_INDEX_LEVEL
    assert index["2026-11-18"].value.index_base == "2020-01-02=100"
    assert str(as_decimal(index["2026-11-18"].value.value)) == "119.47921710"
    assert "2026-11-19" in index
    policy = {r.meta.business_date: r for r in rates_of(plugin, HELD["Policy rate"])}
    assert policy["2026-11-18"].kind == ops.RATE_KIND_FIXING
    assert str(as_decimal(policy["2026-11-18"].value.value)) == "4.5"


def test_generic_yields_benchmark_yields_by_tenor(tmp_path: Path) -> None:
    generic = rates_of(checked(tmp_path), HELD["Generic yields"])
    day = {
        (r.tenor.count, r.tenor.unit): r for r in generic if r.meta.business_date == "2026-11-18"
    }
    months, years = ops.TENOR_UNIT_MONTH, ops.TENOR_UNIT_YEAR
    assert set(day) == {(3, months), (6, months), (12, months), (3, years), (5, years),
                        (7, years), (10, years)}  # fmt: skip
    ten = day[(10, years)]
    assert ten.kind == ops.RATE_KIND_BENCHMARK_YIELD and str(as_decimal(ten.value.value)) == "4.343"
    assert ten.convention.day_count == ops.DAY_COUNT_ACT_365_FIXED
    assert ten.convention.compounding == ops.COMPOUNDING_COMPOUNDED
    assert ten.convention.periods_per_year == 1 and ten.meta.source.dataset == CURVES


def test_the_zero_curve_from_six_months_to_ten_years(tmp_path: Path) -> None:
    zero = rates_of(checked(tmp_path), HELD["Zero coupon yields"])
    day = [r for r in zero if r.meta.business_date == "2026-11-18"]
    assert len(day) == 12 and all(r.kind == ops.RATE_KIND_ZERO for r in day)
    first = next(r for r in day if (r.tenor.count, r.tenor.unit) == (6, ops.TENOR_UNIT_MONTH))
    assert str(as_decimal(first.value.value)) == "4.694"
    assert first.convention.compounding == ops.COMPOUNDING_CONTINUOUS


def test_each_rate_per_unit_in_kroner_hundreds_divided_exactly(tmp_path: Path) -> None:
    plugin = checked(tmp_path)
    prices = {p.meta.row_key: p for b in plugin.on("RecordPrices") for p in b.prices}
    dollar = prices["USDNOK:2026-11-19"]
    assert dollar.meta.subjects[0].entity_id == "LCL-USD" and dollar.kind == ops.PRICE_KIND_CLOSE
    assert str(as_decimal(dollar.price.amount)) == "9.6866" and dollar.price.currency_code == "NOK"
    assert str(as_decimal(prices["JPYNOK:2026-11-18"].price.amount)) == "0.060649"
    assert str(as_decimal(prices["SEKNOK:2026-11-19"].price.amount)) == "0.9552"
    assert dollar.meta.source.dataset == FX and dollar.meta.raw.key.startswith("responses/")
    codes = {k.split(":")[0][:3] for k in prices}
    assert len(codes) == 35 and not codes & {"I44", "TWI", "XDR"}


def test_a_record_not_held_is_reported_missing_and_waits(tmp_path: Path) -> None:
    plugin = checked(tmp_path, "Zero coupon yields")
    missed = {i.value for p in plugin.on("ReportMissingInstrument") for i in p.identifiers}
    assert missed == {"Zero coupon yields"}
    assert not rates_of(plugin, HELD["Zero coupon yields"])


def test_a_past_day_wanted_a_day_with_none_and_a_subject_declined(tmp_path: Path) -> None:
    plugin = resolving(Recorder(INSTANCE))
    work = feed(tmp_path, plugin)
    asyncio.run(work.check())
    for asked in (
        want("w-1", [HELD["NOWA"]], day="2026-10-01"),
        want("w-2", ["INS-ELSE"], day="2026-10-01"),
        want("w-3", [HELD["NOWA"]], day="2026-10-04"),
        want("w-4", [HELD["Generic yields"]], day="2026-10-01", dataset=CURVES),
    ):
        plugin.answer("ObservationsWanted", lambda _, held=asked: held.message)  # type: ignore[misc]
        asyncio.run(plugin.hear(work))
    against = [b for b in plugin.on("RecordRates") if b.want_id == "w-1"]
    assert against and {r.meta.business_date for r in against[0].rates} == {"2026-10-01"}
    generic = [r for b in plugin.on("RecordRates") if b.want_id == "w-4" for r in b.rates]
    assert len(generic) == 7
    reasons = [ops.UnansweredReason.Name(d.reason) for d in plugin.on("DeclineWant")]
    assert reasons == ["UNANSWERED_REASON_NOT_COVERED", "UNANSWERED_REASON_SOURCE_SILENT"]


def test_nothing_recorded_twice_in_a_process(tmp_path: Path) -> None:
    plugin = resolving(Recorder(INSTANCE))
    work = feed(tmp_path, plugin)
    asyncio.run(work.check())
    before = (len(plugin.on("RecordRates")), len(plugin.on("RecordPrices")))
    asyncio.run(work.check())
    assert (len(plugin.on("RecordRates")), len(plugin.on("RecordPrices"))) == before


async def test_a_range_holding_nothing_is_no_data_never_an_error() -> None:
    portal = SyntheticPortal()
    got = await portal.get(path_for("policy", date(2026, 10, 4), date(2026, 10, 4)))
    assert got.status == 404 and got.empty and NO_DATA in got.text


def test_answers_read_as_written() -> None:
    text = (
        "FREQ;Frequency;BASE_CUR;Base Currency;QUOTE_CUR;Quote Currency;TENOR;Tenor;DECIMALS;"
        "CALCULATED;UNIT_MULT;Unit Multiplier;COLLECTION;Collection Indicator;TIME_PERIOD;"
        "OBS_VALUE\n"
        "B;Business;JPY;Japanese yen;NOK;Norwegian krone;SP;Spot;4;false;2;Hundreds;C;x;"
        "2026-11-18;6.0649\n"
        "B;Business;JPY;Japanese yen;NOK;Norwegian krone;SP;Spot;4;false;2;Hundreds;C;x;"
        "2026-11-19;\n"
    )
    read = parse(text, "fx", FX_FLOW)
    (one,) = read.observations
    assert (one.series, one.text, one.unit_mult, one.name) == ("JPY", "6.0649", 2, "Japanese yen")
    assert parse("", "fx", FX_FLOW).observations == []
    try:
        parse("<html>no</html>", "fx", FX_FLOW)
    except NotRead:
        pass
    else:  # pragma: no cover
        raise AssertionError("an answer that is not SDMX-CSV")
    assert within(text, date(2026, 1, 1), date(2026, 1, 2)) is None
