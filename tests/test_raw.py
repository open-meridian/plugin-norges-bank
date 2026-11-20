"""Norges Bank's answers kept as received, where each value was first read, and
months moved past their window."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from meridian import edge

from norges_bank.__main__ import Lake
from norges_bank.portal import FX, ZERO, Fetched, path_for, portal
from norges_bank.raw import RawStore, range_name

from conftest import AT


def fetched(at: datetime) -> Fetched:
    path = path_for(FX, date(2026, 11, 8), date(2026, 11, 18))
    return Fetched(path, 200, b"FREQ;Frequency\n", at, date="Thu, 19 Nov 2026 16:03:32 GMT")


def test_an_answer_kept_and_read_back(tmp_path: Path) -> None:
    store = RawStore(tmp_path)
    key = store.keep(fetched(AT))
    assert key == "responses/2026-11/20261119T220000000000Z-fx-20261108-20261118.json.gz"
    kept = store.read(key)
    assert kept is not None and kept["body"] == "FREQ;Frequency\n" and kept["status"] == 200
    assert kept["url"] == (
        "https://data.norges-bank.no/api/data/EXR/B..NOK.SP?format=csv"
        "&startPeriod=2026-11-08&endPeriod=2026-11-18"
    )
    assert store.read("../outside.json.gz") is None
    assert range_name("/elsewhere") == "answer"
    one = path_for(ZERO, date(2026, 9, 1), date(2026, 10, 28))
    assert range_name(one) == "zero-20260901-20261028"


def test_a_value_names_the_answer_it_was_first_read_from(tmp_path: Path) -> None:
    store = RawStore(tmp_path)
    one, two = store.keep(fetched(AT)), store.keep(fetched(AT + timedelta(hours=6)))
    day = date(2026, 11, 16)
    first, noted = store.noted("NOWA:2026-11-16=2.5", day, one)
    assert noted and first.key == one
    again, noted = store.noted("NOWA:2026-11-16=2.5", day, two)
    assert not noted and again == first
    store.save_firsts()
    # A new process, the same storage: the same answer named.
    assert RawStore(tmp_path).noted("NOWA:2026-11-16=2.5", day, two)[0] == first
    # A revision is a new value, noted afresh.
    assert store.noted("NOWA:2026-11-16=2.75", day, two)[0].key == two


class Mover:
    def __init__(self) -> None:
        self.moved: list[tuple[str, str, int]] = []
        self.stored: list[Any] = []

    async def archive_unit(self, kind: str, unit: str, **span: int) -> None:
        self.moved.append(("archived", unit, span["record_count"]))

    async def delete_unit(self, kind: str, unit: str, **span: int) -> None:
        self.moved.append(("deleted", unit, span["record_count"]))


async def test_months_past_the_window_moved_as_the_setting_says(tmp_path: Path) -> None:
    store = RawStore(tmp_path)
    store.keep(fetched(AT - timedelta(days=400)))
    store.keep(fetched(AT - timedelta(days=399)))
    store.keep(fetched(AT))
    mover = Mover()
    done = await store.tend(mover, 365, "archived", AT)  # type: ignore[arg-type]
    assert done["archived"] == 1
    assert mover.moved == [("archived", "responses/2025-10", 2)]
    kept = await store.tend(mover, 365, "kept", AT)  # type: ignore[arg-type]
    assert kept["kept"] == 1
    assert mover.stored[0].record_count == 3


async def test_nothing_moved_without_granted_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MERIDIAN_STORAGE_DIR", raising=False)
    store = RawStore(None)
    store.keep(fetched(datetime(2020, 1, 1, tzinfo=UTC)))
    mover = Mover()
    assert (await store.tend(mover, 1, "deleted", AT))["deleted"] == 0  # type: ignore[arg-type]
    assert mover.moved == []


async def test_storage_read_once_registered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """On an instance run as shards, storage is read once the plugin has
    registered, from the class's on_start: its shard's own folder, read
    afresh when it registers again (open-meridian 0.37.0). Built before
    Register, as `main()` builds it, nothing is read: read then, it raises."""
    monkeypatch.setenv("MERIDIAN_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("MERIDIAN_PLUGIN_SHARDS", "2")
    monkeypatch.setattr(edge, "_serving", None)
    lake = Lake(portal(False), RawStore())
    monkeypatch.setattr(edge, "_serving", (1, 2))
    await lake.on_start()
    assert lake.raw.granted
    assert lake.raw.root == tmp_path / "shard-1"
    await lake.on_stop()
    monkeypatch.setattr(edge, "_serving", (0, 2))
    await lake.on_start()
    assert lake.raw.root == tmp_path / "shard-0"
