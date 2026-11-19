"""The data suite (meridian.suites), each case Norges Bank's series present
mapped to the plugin's own conversion of Norges Bank's recorded answers, the
whole suite passing.

Presented: the exchange rates' price cases (each a close of the currency's
cash instrument in kroner, exact, a correction the same row's next version,
a currency resolving to two records, a want recorded against and a subject
declined); NOWA's `a-same-day-revision` and `an-index-level` (the Nowa
compounded index); the zero-coupon curve's `a-tenor-not-published`; the
wants and licences cases.

Not presented, each with why: every case about a kind of data Norges Bank
never publishes here (bars, trades, quotes, venues, crypto, outcomes,
chains, filings, holdings, dividends, ratings, pools, derived series); the
calendar cases (no calendar declared); `two-conventions-one-tenor` (the
bills and bonds share one convention), `a-curve-point-from-another-source`,
`a-curve-for-a-date` (it asks for par yields; the curves here are zero
rates and benchmark yields); `a-rate-fixing` (it asks for percentiles, and
Norges Bank publishes none for NOWA); `a-daily-close` and
`reports-its-feed-delay` (Norges Bank states no published time);
`records-a-datasets-liveness`.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from meridian.plugin.v1 import operations_pb2 as ops
from meridian.suites import ANSWERED_BY_SDK, Recorder, run, suite

from norges_bank.portal import Fetched, SyntheticPortal

from conftest import AT, CURVES, FX, HELD, INSTANCE, RATES, feed, resolving, want

NEVER = {
    "bars": "Norges Bank states one rate a day: no open, high, low or volume",
    "a crypto asset's price": "Norges Bank rates currencies: no token",
    "prices on a venue": "Norges Bank's rates are its own, no venue's",
    "a security's price": "Norges Bank rates currencies: no security another source named",
    "trades": "Norges Bank states one rate a day: no trades",
    "quotes": "Norges Bank states one rate a day: no quotes",
    "settlement dates": "records each value as published; never computes a settlement date",
    "outcomes": "Norges Bank publishes no event contract, so no outcome",
    "disputed outcomes": "Norges Bank publishes no event contract, so no outcome disputed",
    "streams": "it polls Norges Bank hourly; it streams nothing",
    "option chains": "Norges Bank publishes no option chain",
    "filings": "Norges Bank publishes rates: no company's filings",
    "holdings": "Norges Bank publishes rates: no holdings report",
    "corporate actions": "Norges Bank publishes rates: no declared dividend",
    "ratings": "Norges Bank publishes rates: no rating",
    "derived series": "the values are recorded as published: no series derived from them",
    "factors": "Norges Bank publishes rates: no pool, so no pool's factor",
    "calendars": "its datasets declare no calendar: the platform holds none for the krone yet",
    "publication times": "Norges Bank states no published time for a value",
}
NOT_PRESENTED = {
    **{c.name: NEVER[c.about] for c in suite("data").cases if c.about in NEVER},
    "two-conventions-one-tenor": "the bills and bonds here share one convention",
    "a-curve-point-from-another-source": "it publishes no curve point another source does",
    "queries-the-lake-within-bounds": "it records no trades",
    "a-daily-close": "Norges Bank states no published time for a rate",
    "a-curve-for-a-date": "the curves here are zero rates and benchmark yields: no par yield",
    "a-rate-fixing": "it asks for percentiles: Norges Bank publishes none for NOWA",
}


class Changed(SyntheticPortal):
    """Norges Bank, read twice: as recorded, then with NOWA of 17 November
    revised and the dollar's rate of 17 November corrected."""

    def __init__(self) -> None:
        super().__init__(lambda: AT)
        self.reads: dict[str, int] = {}

    async def get(self, path: str) -> Fetched:
        got = await super().get(path)
        source = "nowa" if "SHORT_RATES" in path else "fx" if "/EXR/" in path else ""
        self.reads[source] = self.reads.get(source, 0) + 1
        if not source or self.reads[source] == 1:
            return got
        was, now = (
            (";R;Rate;;2;2026-11-17;4.50;", ";R;Rate;;2;2026-11-17;4.52;")
            if source == "nowa"
            else (";2026-11-17;9.6237", ";2026-11-17;9.7000")
        )
        assert got.text.count(was) == 1, was
        return Fetched(path, 200, got.text.replace(was, now).encode(), got.fetched_at, got.date)


class Gap(SyntheticPortal):
    """Norges Bank, the zero curve's 10-year point of 18 November stating
    nothing."""

    async def get(self, path: str) -> Fetched:
        got = await super().get(path)
        if "GOVT_ZEROCOUPON" not in path:
            return got
        lines = [
            line
            for line in got.text.splitlines()
            if not (";10Y;" in line and ";2026-11-18;" in line)
        ]
        return Fetched(path, 200, ("\n".join(lines) + "\n").encode(), got.fetched_at, got.date)


def producers(tmp: Path) -> dict[str, Callable[[Recorder], Awaitable[None]]]:
    async def read(recorder: Recorder) -> None:
        resolving(recorder)
        await feed(tmp, recorder).check()

    async def changed(recorder: Recorder) -> None:
        resolving(recorder)
        work = feed(tmp, recorder, portal=Changed())
        await work.check()
        await work.check()

    async def two_records(recorder: Recorder) -> None:
        resolving(recorder, ambiguous="GBP")
        await feed(tmp, recorder).check()

    async def gap(recorder: Recorder) -> None:
        resolving(recorder)
        await feed(tmp, recorder, portal=Gap(lambda: AT)).check()
        sent = [r for b in recorder.on("RecordRates") for r in b.rates]
        on_28th = {
            (r.tenor.count, r.tenor.unit)
            for r in sent
            if r.meta.business_date == "2026-11-18" and r.kind == ops.RATE_KIND_ZERO
        }
        assert on_28th and (10, ops.TENOR_UNIT_YEAR) not in on_28th

    def wanted(message: Any) -> Callable[[Recorder], Awaitable[None]]:
        async def produce(recorder: Recorder) -> None:
            resolving(recorder)
            work = feed(tmp, recorder)
            await work.check()
            recorder.answer("ObservationsWanted", lambda _: message)
            await recorder.hear(work)

        return produce

    async def licences(recorder: Recorder) -> None:
        recorder.answer(
            "ListDatasets",
            lambda _: ops.ListDatasetsResult(licences=[ops.DatasetLicence(dataset=FX)]),
        )
        work = feed(tmp, recorder)
        await work.wants.read_licences()
        assert work.wants.licensed == {FX}

    async def withdrawn(recorder: Recorder) -> None:
        resolving(recorder)
        work = feed(tmp, recorder)
        recorder.answer(
            "WantWithdrawn", lambda _: ops.WantWithdrawnEvent(want_id="w-s", dataset=RATES)
        )
        await recorder.hear(work)

    close = (ops.PRICE_KIND_CLOSE,)
    return {
        "the-forming-day-restated": changed,
        "an-exact-price": read,
        "an-fx-rate": read,
        "an-asset-that-does-not-resolve": two_records,
        "a-want-recorded-against": wanted(
            want(
                "w-1",
                ["LCL-USD"],
                day="2026-10-01",
                dataset=FX,
                data_type="meridian.v1.Price",
                kinds=close,
            ).message
        ),  # fmt: skip
        "a-subject-declined": wanted(
            want(
                "w-2",
                ["LCL-NOK"],
                day="2026-10-01",
                dataset=FX,
                data_type="meridian.v1.Price",
                kinds=close,
            ).message
        ),  # fmt: skip
        "a-standing-want-withdrawn": withdrawn,
        "reads-its-datasets-licences": licences,
        "a-same-day-revision": changed,
        "an-index-level": read,
        "a-tenor-not-published": gap,
    }


def test_the_data_suite_passes(tmp_path: Path) -> None:
    report = run("data", producers(tmp_path), not_presented=NOT_PRESENTED, instance_id=INSTANCE)
    assert report.passed, report.failures
    assert sorted(report.not_presented) == sorted(NOT_PRESENTED)
    assert len(report.passed_cases) == 11 + len(ANSWERED_BY_SDK)
    assert HELD and CURVES
