"""What this version declares beside its role, `data` (W8.1, W4.1; the
catalogue from contract v18), built from code and used twice: `__main__`
registers with it, and `meridian plugin upload` reads it from the built image
(pyproject.toml's `[tool.meridian] declaration`).

**The catalogue: three datasets** (the product owner, items 128, 130 and
131, 2026-11-19: Tier 1; their keys proposed, the product owner's to
approve), each pushed as Norges Bank publishes it and any past day pulled
when the lake wants it:

- **`norgesbank_rates`**: NOWA, a fixing with its transactions; the Nowa
  compounded index; the policy rate -- rates, daily;
- **`norgesbank_curves`**: the generic yields, `benchmark_yield` at each
  tenor on the generic curve's record (ruling 130), and the zero-coupon
  curve, `zero` rates from 6 months to 10 years -- rates, daily;
- **`norgesbank_fx`**: the daily exchange rates, each the price of a
  currency's cash instrument in Norwegian kroner -- prices, daily.

Each: `vendor` Norges Bank, no aggregator; `modes` `push` and `pull`; its
day Oslo's (Norges Bank's business day), ending at midnight; no calendar
(the platform holds none for the krone yet); no venue; `history` 0, as each
series states; its terms and pricing (contract 30, ruling 1032) Norges
Bank's, in plain words, and no licence declared -- a deployment's licence,
set on the Data sources page, is the one enforced; a gap asked again
(`gap_recovery` `backfill`, W10.14). Norges Bank's "no change to the
content" condition sits with the derived-data flag of the deployment's
licence, as the research rules it.

**Storage:** the answers (raw.py), archivable, ten years by default.
"""

from __future__ import annotations

from meridian import DatasetDeclaration
from meridian.declaration import RecordKind

from .raw import DEFAULT_WINDOW_DAYS, RESPONSES

NORGESBANK_RATES = "norgesbank_rates"
NORGESBANK_CURVES = "norgesbank_curves"
NORGESBANK_FX = "norgesbank_fx"
KEYS = (NORGESBANK_RATES, NORGESBANK_CURVES, NORGESBANK_FX)
VENDOR = "Norges Bank"
RATE = "meridian.v1.Rate"
PRICE = "meridian.v1.Price"
CADENCE = 86_400
DAY_TIME_ZONE = "Europe/Oslo"
DAY_END_MINUTE = 0

#: Norges Bank's terms, in plain words (contract 30, ruling 1032), from its
#: disclaimer and its NOWA FAQ, as the research read them on 2026-11-19.
TERMS_ALL = (
    "Norges Bank's open data API: free, no key or account. Its content may be copied with "
    "Norges Bank quoted as the source and no change to the content; no inline linking; Norges "
    "Bank accepts no liability (https://www.norges-bank.no/en/disclaimer/). Commercial use is "
    "not addressed. No rate limit is stated."
)
TERMS = {
    NORGESBANK_RATES: TERMS_ALL
    + (
        " NOWA is published free and needs no licence "
        "(https://www.norges-bank.no/en/topics/liquidity-and-markets/nowa/faq-nowa/)."
    ),
    NORGESBANK_CURVES: TERMS_ALL
    + (
        " The generic yields are the mid-yields in the interdealer market at 16:00; the "
        "zero-coupon yields are Norges Bank's estimates by the Nelson-Siegel-Svensson method. "
        "This dataset carries no forward rate or curve parameter."
    ),
    NORGESBANK_FX: TERMS_ALL
    + (
        " The exchange rates are Norges Bank's at the ECB's concertation, 14:15 CET; a rate "
        "stated per hundred units is recorded per unit, divided exactly."
    ),
}


def _dataset(key: str, data_types: list[str]) -> DatasetDeclaration:
    return DatasetDeclaration(
        key=key,
        vendor=VENDOR,
        data_types=data_types,
        modes=["push", "pull"],
        cadence=CADENCE,
        history=0,
        terms_and_pricing=TERMS[key],
        gap_recovery="backfill",
        day_time_zone=DAY_TIME_ZONE,
        day_end_minute=DAY_END_MINUTE,
    )


CATALOGUE = [
    _dataset(NORGESBANK_RATES, [RATE, "meridian.v1.Rate.transaction_count"]),
    _dataset(NORGESBANK_CURVES, [RATE]),
    _dataset(NORGESBANK_FX, [PRICE]),
]

RESPONSES_KIND = RecordKind(RESPONSES, "Raw responses", window_days=DEFAULT_WINDOW_DAYS)
