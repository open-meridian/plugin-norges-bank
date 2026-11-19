"""Norges Bank's answers, read as Norges Bank wrote them.

Its open data API (https://data.norges-bank.no/api/) answers a data request
with `format=csv` as SDMX-CSV separated by semicolons: a header line naming
each dimension's code and, beside most, its label (`FREQ;Frequency;
BASE_CUR;Base Currency;...`), then `TIME_PERIOD` and `OBS_VALUE`, then one
line a series a day. Each line is read by the header's codes:

- **NOWA and its index** (`SHORT_RATES`): `INSTRUMENT_TYPE`, `TENOR`,
  `UNIT_MEASURE` -- `NOWA.ON.R` the rate, `NOWA.ON.T` its transactions,
  `NOWA.1D.I` the index;
- **the policy rate** (`IR`): the same, `KPRA.SD.R`;
- **the generic yields** (`GOVT_GENERIC_RATES`): `INSTRUMENT_TYPE` and
  `TENOR`, `GBON.10Y`;
- **the zero-coupon curve** (`GOVT_ZEROCOUPON`): `TENOR`, `ZC.10Y`;
- **the exchange rates** (`EXR`): `BASE_CUR`, `USD`, with `UNIT_MULT` (0
  units, 2 hundreds).

A line with no value is no value, never a zero. A value is kept as the text
Norges Bank wrote, and read as a `Decimal` from it, never a float; one that
does not read is kept as not read, and never recorded.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

MISSING = {"", "NaN", "na", "NA"}
NOWA_FLOW, POLICY_FLOW, GENERIC_FLOW, ZERO_FLOW, FX_FLOW = (
    "SHORT_RATES", "IR", "GOVT_GENERIC_RATES", "GOVT_ZEROCOUPON", "EXR",
)  # fmt: skip


class NotRead(Exception):  # noqa: N818 - what the answer was not
    """An answer that is not what was asked for."""


@dataclass(frozen=True)
class Observation:
    """One value as Norges Bank stated it: its series, day and text; a
    curve point's tenor; an exchange rate's unit multiplier and its
    currency's name."""

    series: str
    day: date
    text: str
    tenor: str = ""
    unit_mult: int = 0
    name: str = ""

    @property
    def value(self) -> Decimal:
        return Decimal(self.text)


@dataclass
class Observations:
    """An answer read: its values in order, and the values that did not read."""

    source: str
    observations: list[Observation] = field(default_factory=list)
    unread: list[str] = field(default_factory=list)

    @property
    def days(self) -> list[date]:
        return sorted({o.day for o in self.observations})

    def on(self, day: date) -> dict[str, Observation]:
        return {o.series: o for o in self.observations if o.day == day}


def _number(text: str) -> bool:
    try:
        return Decimal(text).is_finite()
    except InvalidOperation:
        return False


def _series(flow: str, row: dict[str, str]) -> tuple[str, str]:
    """A line's series, and its tenor where it is a curve's point."""
    if flow in (NOWA_FLOW, POLICY_FLOW):
        held = (row.get("INSTRUMENT_TYPE", ""), row.get("TENOR", ""), row.get("UNIT_MEASURE", ""))
        return ".".join(held), ""
    if flow == GENERIC_FLOW:
        tenor = row.get("TENOR", "")
        return f"{row.get('INSTRUMENT_TYPE', '')}.{tenor}", tenor
    if flow == ZERO_FLOW:
        tenor = row.get("TENOR", "")
        return f"ZC.{tenor}", tenor
    return row.get("BASE_CUR", ""), ""


def parse(text: str, source: str, flow: str) -> Observations:
    """An SDMX-CSV answer of `flow`, read; NotRead where it is not one. An
    answer holding no line (a day nothing was published) reads as none."""
    read = Observations(source)
    body = text.lstrip("﻿")
    if not body.strip():
        return read
    rows = list(csv.reader(io.StringIO(body), delimiter=";"))
    header = [h.strip() for h in rows[0]]
    if "TIME_PERIOD" not in header or "OBS_VALUE" not in header:
        raise NotRead(f"the answer is not SDMX-CSV: {text[:80]!r}")
    for cells in rows[1:]:
        if not cells or not any(c.strip() for c in cells):
            continue
        row: dict[str, str] = {}
        for name, cell in zip(header, cells, strict=False):
            row.setdefault(name, cell.strip())
        series, tenor = _series(flow, row)
        try:
            day = date.fromisoformat(row.get("TIME_PERIOD", ""))
        except ValueError:
            read.unread.append(f"{series}: a day {row.get('TIME_PERIOD', '')[:20]!r}")
            continue
        said = row.get("OBS_VALUE", "")
        if said in MISSING:
            continue
        if not _number(said):
            read.unread.append(f"{series} {day}: {said[:40]!r}")
            continue
        unit = row.get("UNIT_MULT", "0")
        read.observations.append(
            Observation(
                series,
                day,
                said,
                tenor,
                int(unit) if unit.isdigit() else 0,
                row.get("Base Currency", ""),
            )
        )
    read.observations.sort(key=lambda o: (o.series, o.day))
    return read
