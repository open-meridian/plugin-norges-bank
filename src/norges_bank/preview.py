"""The pages on sample data, each printed as one HTML file:
for looking at them without a deployment.

    python -m norges_bank.preview connection > preview/connection.html

The plugin's work runs on the SDK's suite recorder in place of a sidecar --
NOWA's record and every currency resolved, every other record to none (so
the "not held" state shows), every batch recorded -- against the answers
committed under responses/, at 22:00 UTC on 19 November 2026: the current
ranges read, a want for NOWA of 1 October answered, and one for a Sunday
declined. `connection-sources` and `datasets-records` are each page's second
tab; `connection-first` and `datasets-first` the pages before the first
check.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime

from meridian.plugin.v1 import operations_pb2 as ops
from meridian.receive import Heard
from meridian.suites import Recorder
from meridian.testing import PageClient

from .feed import Feed
from .page import CONNECTION, DATASETS_PAGE, hold, pages
from .portal import SyntheticPortal
from .raw import RawStore

AT = datetime(2026, 11, 19, 22, 0, tzinfo=UTC)
PAGES = {
    "connection": CONNECTION,
    "connection-sources": CONNECTION,
    "datasets": DATASETS_PAGE,
    "datasets-records": DATASETS_PAGE,
    "datasets-search": DATASETS_PAGE,
    "connection-first": CONNECTION,
    "datasets-first": DATASETS_PAGE,
}
TABS = {"connection-sources": "sources", "datasets-records": "records"}
SEARCHED = "dollar"
NOWA_ID = "LCL-NOWA"


def _want(want_id: str, day: str) -> Heard:  # type: ignore[type-arg]
    return Heard(
        row="ObservationsWanted",
        message=ops.ObservationsWantedEvent(
            want_id=want_id,
            dataset="norges-bank:norgesbank_rates",
            data_type="meridian.v1.Rate",
            subjects=[ops.SubjectRef(entity_id=NOWA_ID)],
            business_date=day,
        ),
    )


def _feed() -> Feed:
    recorder = Recorder("norges-bank")

    def resolved(params: ops.ResolveIdentifierParams) -> ops.ResolveIdentifierResult:
        named = params.identifiers[0]
        if named.scheme == "iso4217":
            return ops.ResolveIdentifierResult(found=True, instrument_id=f"LCL-{named.value}")
        if named.value == "NOWA":
            return ops.ResolveIdentifierResult(found=True, instrument_id=NOWA_ID)
        return ops.ResolveIdentifierResult(found=False, miss_reason=ops.MISS_REASON_NOT_FOUND)

    recorder.answer("ResolveIdentifier", resolved)
    return recorder.bind(Feed(SyntheticPortal(lambda: AT), RawStore(), now=lambda: AT))


async def synthetic_feed() -> Feed:
    feed = _feed()
    await feed.check()
    await feed.on_observations_wanted(_want("want-1001", "2026-10-01"))
    await feed.on_observations_wanted(_want("want-1004", "2026-10-04"))
    return feed


def render(page: str) -> str:
    feed = _feed() if page.endswith("-first") else asyncio.run(synthetic_feed())
    hold(feed)
    query = {"q": SEARCHED} if page == "datasets-search" else {}
    if page in TABS:
        query = {"tab": TABS[page]}
    answer = PageClient(pages).get(PAGES[page], "admin", **query)
    if answer.status != 200:
        raise SystemExit(f"{page} answered {answer.status}: {answer.text[:200]}")
    return answer.text


def main() -> None:
    page = sys.argv[1] if len(sys.argv) > 1 else "connection"
    if page not in PAGES:
        raise SystemExit(f"no page {page!r}: {', '.join(PAGES)}")
    sys.stdout.write(render(page))


if __name__ == "__main__":
    main()
