"""The catalogue, from code, as the deployment approves it."""

from __future__ import annotations

from norges_bank.declaration import DECLARATION


def test_three_datasets_rates_and_prices_pushed_and_pulled() -> None:
    keys = [d.key for d in DECLARATION.catalogue]
    assert keys == ["norgesbank_rates", "norgesbank_curves", "norgesbank_fx"]
    kinds = {d.key: list(d.data_types)[0] for d in DECLARATION.catalogue}
    assert kinds["norgesbank_fx"] == "meridian.v1.Price"
    assert kinds["norgesbank_curves"] == "meridian.v1.Rate"
    for dataset in DECLARATION.catalogue:
        assert dataset.day_time_zone == "Europe/Oslo" and dataset.vendor == "Norges Bank"
        assert dataset.gap_recovery == "backfill" and not dataset.calendar_id
        assert len(list(dataset.modes)) == 2
        said = dataset.terms_and_pricing
        assert "Norges Bank quoted as the source" in said and "no change to the content" in said
        assert len(said) <= 2000
    assert "needs no licence" in DECLARATION.catalogue[0].terms_and_pricing


def test_the_answers_are_kept_in_storage() -> None:
    assert DECLARATION.storage is not None
    assert [k.name for k in DECLARATION.storage.kinds] == ["responses"]
