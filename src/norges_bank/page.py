"""The plugin's pages, under Manage alone: the data role's common pages
(spec/plugin-pages-follow-their-role), Connection and Datasets, in its
order, each also a read tool for agents on the deployment's MCP under the
role's names (`read_connection`, `read_datasets`). Each record is the
role's (`meridian.roles.data`), extended with Norges Bank's fields;
each template is the role's, with Norges Bank's nuance at its blocks only, as
plugin-ecb's are.

A data plugin shows its connectivity, its data subscriptions and how its
entitlements resolve, and no market data (the product owner, 2026-10-03):

- **Connection** (`/`): "Key" -- the mode (Live or Sample data), "No key
  needed", what Norges Bank serves; "Limits and use" -- Norges Bank states
  no figure, the requests made, the last check and error; "Stream": it does not
  stream. Then a tab of its own (`?tab=sources`), **Sources**, one line per
  source -- NOWA and its index, the policy rate, the generic yields, the
  zero-coupon curve and the exchange rates: its state, the latest day published, its calls, its last
  error, and in its detail where it reads.
- **Datasets** (`/datasets`): "Served", "Wants" and "Subjects", each with
  the three datasets; then a tab of its own (`?tab=records`), **Records**:
  each record and currency, with its convention and the deployment's
  instrument for it or why there is none -- one line a row, searched and paged
  by the kit's om-pager to fit one screen.

Neither shows a rate or a level: those are the reading roles' to show.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import meridian
from meridian.roles import data

from . import records
from .declared import CATALOGUE
from .feed import DATASETS, Feed, SourceStatus, Status
from .portal import BASE, FX, GENERIC, NOWA, PATHS, POLICY, SOURCES, ZERO
from .series import GENERIC_RECORD, NOT_CARRIED, NOWA_INDEX_RECORD, POLICY_RECORD, ZERO_RECORD

TITLE = "Norges Bank"
#: The kit these pages are built on: 0.12.0's "Facts" and "Next step".
KIT = "0.12.0"

pages = meridian.Pages(TITLE, templates=Path(__file__).parent / "templates", kit=KIT)

CONNECTION = "/"
DATASETS_PAGE = "/datasets"

MOST_QUERY = 100
CONNECTION_TABS = {"connection": "Connection", "sources": "Sources"}
TABS = {"served": "Served", "records": "Records"}
#: The attribution Norges Bank's terms ask for.
ATTRIBUTION = "Source: Norges Bank. Copied with no change to the content."
SOURCE_NAMES = {
    NOWA: "NOWA and its compounded index",
    POLICY: "The policy rate",
    GENERIC: "Generic yields",
    ZERO: "Zero coupon yields",
    FX: "Exchange rates against the krone",
}
SHORT_NAMES = {
    NOWA: "NOWA",
    POLICY: "Policy rate",
    GENERIC: "Generic yields",
    ZERO: "Zero curve",
    FX: "Exchange rates",
}
#: Each source's line in Sources, named by its source: two share a dataset.
PUBLISHED = {
    NOWA: "NOWA at 09:00 the next banking day, its index with it",
    POLICY: "each business day; it changes on decision days",
    GENERIC: "each business day after 09:00, the previous day's",
    ZERO: "each business day after 09:00, the previous day's",
    FX: "each business day at about 16:00",
}
CONVENTIONS = {
    "rates": "actual/365, simple, as Norges Bank publishes NOWA",
    "policy": "actual/365, simple: the plugin's statement; Norges Bank states per cent",
    "index": "an index level, based 2 January 2020 = 100, compounding NOWA actual/365",
    GENERIC: "effective: annual on actual/365, as Norges Bank's bill terms state it",
    ZERO: "continuously compounded: the plugin's statement of the NSS form",
    FX: "kroner per unit of the currency; a rate stated per hundred divided exactly",
}

_held: dict[str, Any] = {}


def hold(feed: Feed) -> None:
    """The feed the pages read, once the plugin has registered."""
    _held["feed"] = feed


def _status() -> tuple[Status, Feed | None]:
    feed: Feed | None = _held.get("feed")
    return (feed.status if feed is not None else Status(), feed)


def _iso(moment: datetime | None) -> str:
    return moment.astimezone(UTC).isoformat(timespec="seconds") if moment else ""


def _day(day: date | None) -> str:
    return day.isoformat() if day else ""


def _source_state(held: SourceStatus, mode: str) -> str:
    if held.error and held.read_at is None:
        return "Not answering"
    if held.error:
        return "Answering"
    if held.read_at is None:
        return "Checking Norges Bank"
    return "Sample data" if mode == "synthetic" else "Answering"


def _state(status: Status) -> tuple[str, str, str]:
    """The head's status: its state, what it means, and its detail."""
    error = status.error
    if error and not status.read:
        return "error", "Not answering", error
    if error:
        return "warn", "Answering", error
    if not status.read:
        return "busy", "Checking Norges Bank", ""
    misses = [h.code for h in [*status.records.values(), *status.currencies.values()] if h.miss]
    if misses:
        plural = "record" if len(misses) == 1 else "records"
        more = ", …" if len(misses) > 6 else ""
        return "warn", f"{len(misses)} {plural} not held", ", ".join(sorted(misses)[:6]) + more
    if status.mode == "synthetic":
        return "ok", "Sample data", ""
    return "ok", "Answering", ""


def _source(source: str, status: Status, instance: str) -> records.SourceRead:
    held = status.sources[source]
    return records.SourceRead(
        source=SOURCE_NAMES[source],
        dataset=f"{instance}:{DATASETS[source]}",
        kind=source,
        state=_source_state(held, status.mode),
        last_release=_day(held.latest_day),
        calls=held.fetches,
        last_error=held.error,
        reads=(
            "The answer recorded on 2026-11-19, committed with the plugin"
            if status.mode == "synthetic"
            else BASE + PATHS[source].split("?")[0]
        ),
        history=f"Published {PUBLISHED[source]}; any past day pulled when the lake wants it",
    )


def connection_read(status: Status, feed: Feed | None) -> records.ConnectionRead:
    state, said, _ = _state(status)
    kept = feed.raw.keys() if feed is not None else []
    window = ""
    if feed is not None and feed.raw.granted:
        window = "in the storage the deployment grants, as its responses settings say"
    elif feed is not None:
        window = "in a directory of the plugin's own: this deployment grants no storage"
    instance = feed.plugin.identity.instance_id if feed is not None else "norges-bank"
    answered = status.read or status.mode == "synthetic"
    return records.ConnectionRead(
        mode="Sample data" if status.mode == "synthetic" else "Live",
        credentials=[],
        entitled_at_vendor=(
            "NOWA, its index, the policy rate, the generic yields, the zero-coupon curve and "
            "the exchange rates: no key"
            if answered
            else ""
        ),
        limit=(
            "Norges Bank states no limit; the plugin asks one request at a time, at most one "
            "every two seconds, and checks for new values every hour"
        ),
        calls=status.fetches,
        last_call_at=_iso(status.checked_at),
        last_error=status.error,
        sessions=None,
        state=state,
        said=said,
        source=(
            "The answers recorded on 2026-11-19, committed with the plugin"
            if status.mode == "synthetic"
            else f"{BASE}/api: its SDMX dataflows"
        ),
        checked_at=_iso(status.checked_at),
        sources=[_source(source, status, instance) for source in SOURCES],
        responses_kept=len(kept),
        kept_for=window,
    )


def _record_dataset(code: str) -> tuple[str, str, str]:
    """A record's dataset, what it is recorded as, and its convention."""
    if code == GENERIC_RECORD.code:
        return DATASETS[GENERIC], "benchmark yields at 3 months to 10 years", CONVENTIONS[GENERIC]
    if code == ZERO_RECORD.code:
        return DATASETS[ZERO], "zero rates at 6 months to 10 years", CONVENTIONS[ZERO]
    if code == NOWA_INDEX_RECORD.code:
        return DATASETS[NOWA], "index levels", CONVENTIONS["index"]
    if code == POLICY_RECORD.code:
        return DATASETS[POLICY], "fixings", CONVENTIONS["policy"]
    return DATASETS[NOWA], "fixings, with transactions", CONVENTIONS["rates"]


def datasets_read(status: Status, feed: Feed | None) -> records.DatasetsRead:
    instance = feed.plugin.identity.instance_id if feed is not None else "norges-bank"
    answered = status.read or status.mode == "synthetic"
    served = data.served(
        CATALOGUE,
        instance,
        feed.wants if feed is not None else None,
        "Yes: no key needed" if answered else "Not asked yet",
    )
    rows = [
        records.RecordRead(
            code=h.code,
            name=h.name,
            dataset=_record_dataset(h.code)[0],
            recorded_as=_record_dataset(h.code)[1],
            convention=_record_dataset(h.code)[2],
            instrument_id=h.instrument_id,
            miss=h.miss,
            latest_day=_day(h.latest_day),
        )
        for h in status.records.values()
    ]
    rows += [
        records.RecordRead(
            code=h.code,
            name=h.name,
            dataset=DATASETS[FX],
            recorded_as="its price in NOK, a close",
            convention=CONVENTIONS[FX],
            instrument_id=h.instrument_id,
            miss=h.miss.replace("_", " "),
            latest_day=_day(h.latest_day),
        )
        for h in sorted(status.currencies.values(), key=lambda c: c.code)
    ]
    rows += [
        records.RecordRead(
            code=series,
            name=why,
            dataset=DATASETS[FX] if series in ("I44, TWI", "XDR") else DATASETS[NOWA],
            recorded_as="not carried",
            convention="",
            instrument_id="",
            miss="not carried",
        )
        for series, why in NOT_CARRIED.items()
        if status.sources[NOWA].read_at
    ]
    return records.DatasetsRead(
        served=served,
        wants=list(data.want_rows(feed.wants)) if feed is not None else [],
        reads_instruments=True,
        attribution=ATTRIBUTION,
        records=rows,
        unread=[
            f"{line} ({n} reads)"
            for held in status.sources.values()
            for line, n in sorted(held.unread.items())
        ],
    )


def figures(status: Status, feed: Feed | None) -> list[meridian.Figure]:
    """The data role's figures, in its order (`meridian.roles.data`); the
    plugin reports none of its own."""
    state, said, why = _state(status)
    if status.mode == "synthetic" and state == "ok":
        connection: Any = "Sample data"
    elif said == "Not answering":
        connection = meridian.Figure("", said, state="error", why=why[:200])
    else:
        error = status.error
        connection = meridian.Figure(
            "", "Answering", state="warn" if error else None, why=error[:200]
        )
    last = feed.wants.counts.last_ns if feed is not None else 0
    return data.figures(
        connection=connection,
        entitled_at_vendor=f"{len(CATALOGUE)} of {len(CATALOGUE)} datasets",
        stream="Does not stream",
        last_recorded=(datetime.fromtimestamp(last / 10**9, UTC) if last else None),
    )


def _moment(value: str) -> str:
    """An ISO moment as a person reads it, to the minute in UTC."""
    if not value:
        return ""
    if len(value) == 10:
        return value
    return datetime.fromisoformat(value).astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


def _weekday(value: str) -> str:
    return date.fromisoformat(value).strftime("%a %d %b %Y") if value else ""


def matching(query: str, *texts: str) -> bool:
    """Whether every word of a search is in one of `texts`, case aside."""
    words = query.lower().split()
    held = " ".join(texts).lower()
    return all(word in held for word in words)


pages.environment.filters["moment"] = _moment
pages.environment.filters["day"] = _weekday


@pages.page(
    CONNECTION,
    "Connection",
    levels="admin",
    answers=records.ConnectionRead,
    name="read_connection",
    description=(
        "How this plugin reaches Norges Bank's open data API, as every data plugin's "
        "Connection answers it: the mode (Live or Sample data), no key needed, what Norges "
        "Bank serves, its limits and the requests made, the last check and why it failed if "
        "it did; it does not stream. Then Norges Bank's own: each source -- NOWA and its "
        "index, the policy rate, the generic yields, the zero-coupon curve and the exchange "
        "rates -- with its state, the latest day it published, its calls and last error; "
        "and how many answers are kept. No rate."
    ),
)
async def connection(request: meridian.Request) -> meridian.Response:
    status, feed = _status()
    read = connection_read(status, feed)
    tab = request.query.get("tab", "connection")
    return pages.answer(
        "connection.html",
        read,
        detail=_state(status)[2],
        # Named apart from the SDK's own `tab` and `tabs` (0.32.3), which
        # would draw the data role's section row in their place.
        view=tab if tab in CONNECTION_TABS else "connection",
        views=CONNECTION_TABS,
        short=SHORT_NAMES,
    )


@pages.page(
    DATASETS_PAGE,
    "Datasets",
    levels="admin",
    answers=records.DatasetsRead,
    name="read_datasets",
    description=(
        "What this plugin serves the lake, as every data plugin's Datasets answers it: its "
        "three datasets as the catalogue declares them (NOWA, its index and the policy "
        "rate; the generic yields and the zero-coupon curve; the exchange rates, prices), "
        "whether a deployment admin has licensed each, what it recorded and declined; the "
        "standing wants it keeps current and the wants it answered. Then Norges Bank's own: "
        "the attribution its terms ask for, and each record and currency with its "
        "convention and the deployment's instrument for it or why there is none. No rate."
    ),
)
async def datasets(request: meridian.Request) -> meridian.Response:
    status, feed = _status()
    read = datasets_read(status, feed)
    # A browser draws one tab, its search narrowing the records drawn; a
    # tool answers every tab.
    query = request.query.get("q", "").strip()[:MOST_QUERY]
    tab = request.query.get("tab", "served")
    tab = "records" if query else tab if tab in TABS else "served"
    shown = [r for r in read.records if matching(query, r.code, r.name, r.dataset)]
    return pages.answer(
        "datasets.html",
        read,
        query=query,
        tab=tab,
        tabs=TABS,
        shown=shown,
        state=_state(status),
        checked_at=_iso(status.checked_at),
    )
