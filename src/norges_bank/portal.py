"""Norges Bank's open data API, at data.norges-bank.no, and its stand-in.

Five requests are made, each for a range of days, as SDMX-CSV
(`format=csv`), and nothing else:

- NOWA, its transactions and its compounded index --
  `/api/data/SHORT_RATES/B.NOWA..?format=csv&startPeriod=...&endPeriod=...`;
- the policy rate -- `/api/data/IR/B.KPRA.SD.R?...`;
- the generic yields -- `/api/data/GOVT_GENERIC_RATES/B...?...`;
- the zero-coupon curve -- `/api/data/GOVT_ZEROCOUPON/B..?...`;
- the exchange rates against the krone -- `/api/data/EXR/B..NOK.SP?...`.

A range holding nothing is answered 404 with SDMX's error code 100, "No data
for data query": no values, never an error.

Read from Norges Bank itself: no key, no account. Its terms state no rate
limit (docs/terms.md); the plugin asks one request at a time, at most one
every two seconds, says who it is in its User-Agent, and checks hourly.

`SyntheticPortal` answers from the real responses committed under
responses/ (responses/index.json), recorded on 2026-11-19: each dataflow
from 3 August to 19 November 2026. A range is answered with the recorded
lines in it, and each current range ends on its recording's last day
whatever the clock says, so the plugin's tests and its e2e run on it,
offline, the same on any day.
"""

from __future__ import annotations

import asyncio
import csv
import gzip
import io
import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from importlib import resources
from typing import Protocol

from .sdmx import FX_FLOW, GENERIC_FLOW, NOWA_FLOW, POLICY_FLOW, ZERO_FLOW

BASE = "https://data.norges-bank.no"
NOWA, POLICY, GENERIC, ZERO, FX = "nowa", "policy", "generic", "zero", "fx"
SOURCES = (NOWA, POLICY, GENERIC, ZERO, FX)
#: Each source's dataflow, and its key.
FLOWS = {
    NOWA: (NOWA_FLOW, "B.NOWA.."),
    POLICY: (POLICY_FLOW, "B.KPRA.SD.R"),
    GENERIC: (GENERIC_FLOW, "B..."),
    ZERO: (ZERO_FLOW, "B.."),
    FX: (FX_FLOW, "B..NOK.SP"),
}
PATHS = {source: f"/api/data/{flow}/{key}?format=csv" for source, (flow, key) in FLOWS.items()}
USER_AGENT = "meridian-norges-bank (+https://github.com/open-meridian/plugin-norges-bank)"
SPACING = 2.0
TIMEOUT = 60.0
MOST_BYTES = 16 * 1024 * 1024
#: How far each current range reaches back: ten days.
CURRENT_DAYS = 10
#: SDMX's error code for a range holding nothing.
NO_DATA = 'code="100"'


def path_for(source: str, start: date, end: date) -> str:
    """The address of `source`'s values from `start` to `end`."""
    return f"{PATHS[source]}&startPeriod={start.isoformat()}&endPeriod={end.isoformat()}"


def source_of(path: str) -> str:
    """Which source an address asks."""
    return next((s for s, at in PATHS.items() if path.startswith(at)), "")


class PortalUnreachable(Exception):  # noqa: N818 - what Norges Bank's API was
    """The API could not be asked: no answer, or not in time."""


@dataclass(frozen=True)
class Fetched:
    """One answer, as received."""

    path: str
    status: int
    body: bytes
    fetched_at: datetime
    date: str = ""

    @property
    def url(self) -> str:
        return BASE + self.path

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    @property
    def empty(self) -> bool:
        """Whether it says the range holds nothing."""
        return self.status == 404 and NO_DATA in self.text


class Portal(Protocol):
    mode: str

    def current(self, today: date, source: str) -> tuple[date, date]: ...

    async def get(self, path: str) -> Fetched: ...


def utc_now() -> datetime:
    return datetime.now(UTC)


class LivePortal:
    """Norges Bank's API itself."""

    mode = "live"

    def __init__(self, now: Callable[[], datetime] = utc_now) -> None:
        self._now = now
        self._lock = asyncio.Lock()
        self._last = 0.0

    def current(self, today: date, source: str) -> tuple[date, date]:
        return today - timedelta(days=CURRENT_DAYS), today

    async def get(self, path: str) -> Fetched:
        async with self._lock:
            wait = self._last + SPACING - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            try:
                return await asyncio.to_thread(self._get, path)
            finally:
                self._last = time.monotonic()

    def _get(self, path: str) -> Fetched:
        request = urllib.request.Request(BASE + path, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as answer:  # noqa: S310 - Norges Bank's https address
                body = answer.read(MOST_BYTES + 1)
                status = answer.status
                said = answer.headers
        except urllib.error.HTTPError as refused:
            body = refused.read(MOST_BYTES + 1) if refused.fp else b""
            status, said = refused.code, refused.headers
        except (urllib.error.URLError, TimeoutError, OSError) as failed:
            reason = getattr(failed, "reason", failed)
            raise PortalUnreachable(f"{BASE}{path[:80]}: {type(reason).__name__}") from failed
        if len(body) > MOST_BYTES:
            raise PortalUnreachable(f"{BASE}{path[:80]}: answered more than {MOST_BYTES} bytes")
        return Fetched(path, status, body, self._now(), date=said.get("Date", "") if said else "")


@dataclass(frozen=True)
class Recording:
    """One recorded answer, its Date and last day."""

    text: str
    said: str
    last_day: date


class SyntheticPortal:
    """The responses committed under responses/: each range answered with
    the recorded lines in it, under its recording's Date."""

    mode = "synthetic"

    def __init__(self, now: Callable[[], datetime] = utc_now) -> None:
        self._now = now
        held = resources.files(__package__).joinpath("responses")
        index = json.loads(held.joinpath("index.json").read_text(encoding="utf-8"))
        self.recordings = {
            source: Recording(
                gzip.decompress(held.joinpath(index[source]["file"]).read_bytes()).decode(),
                str(index[source]["date"]),
                date.fromisoformat(index[source]["last_day"]),
            )
            for source in SOURCES
        }
        self.asked: list[str] = []

    def current(self, today: date, source: str) -> tuple[date, date]:
        last = self.recordings[source].last_day
        return last - timedelta(days=CURRENT_DAYS), last

    async def get(self, path: str) -> Fetched:
        self.asked.append(path)
        recording = self.recordings.get(source_of(path))
        if recording is None:
            return Fetched(path, 404, b"Not found", self._now())
        query = dict(p.partition("=")[::2] for p in path.partition("?")[2].split("&"))
        try:
            start = date.fromisoformat(query.get("startPeriod", ""))
            end = date.fromisoformat(query.get("endPeriod", ""))
        except ValueError:
            return Fetched(path, 400, b"Bad period", self._now())
        body = within(recording.text, start, end)
        if body is None:
            return Fetched(path, 404, f"{NO_DATA}: No data for data query".encode(), self._now())
        return Fetched(path, 200, body.encode(), self._now(), recording.said)


def within(text: str, start: date, end: date) -> str | None:
    """A recorded answer's lines from `start` to `end`, as Norges Bank wrote
    them; None where it holds none."""
    lines = text.splitlines()
    header = next(csv.reader(io.StringIO(lines[0]), delimiter=";"))
    at = header.index("TIME_PERIOD")
    kept = [lines[0]]
    for line in lines[1:]:
        cells = next(csv.reader(io.StringIO(line), delimiter=";"), [])
        try:
            day = date.fromisoformat(cells[at])
        except (IndexError, ValueError):
            continue
        if start <= day <= end:
            kept.append(line)
    return "\n".join(kept) + "\n" if len(kept) > 1 else None


def portal(synthetic: bool, now: Callable[[], datetime] = utc_now) -> Portal:
    return SyntheticPortal(now) if synthetic else LivePortal(now)
