"""Norges Bank's series this version carries, what each one is, and the
record it is recorded against: the plugin's series map.

**Rates** (`norgesbank_rates`). NOWA (`SHORT_RATES`, `B.NOWA.ON.R`), a daily
`fixing` with its number of transactions (`B.NOWA.ON.T`), in per cent,
actual/365 simple: Norges Bank publishes it "as an annualised interest rate
(ACT/365) rounded to two decimal places"
(https://www.norges-bank.no/en/topics/liquidity-and-markets/nowa/principles-for-calculating-and-publishing-nowa/),
as plugin-bis's NO row states it. Its volume (`B.NOWA.ON.V`) is **not
carried**: Norges Bank states no unit for it. The Nowa compounded index
(`B.NOWA.1D.I`), an `index_level` based 2 January 2020 = 100, compounding
NOWA actual/365 (https://www.norges-bank.no/en/topics/statistics/nowa-data/nowa-index/).
The policy rate (`IR`, `B.KPRA.SD.R`), a `fixing`, the rate on banks'
sight deposits at Norges Bank, in the same convention -- the plugin's
statement; Norges Bank states per cent.

**Generic yields** (`norgesbank_curves`, `GOVT_GENERIC_RATES`). "The generic
yield is the effective yield on the government security closest to the
stated maturity": Treasury bills at 3, 6 and 12 months and government bonds
at 3, 5, 7 and 10 years, each a quoted security's yield, so each a
`benchmark_yield` (ruling 130) at its tenor on one `rate_curve` record, the
mid-yield in the interdealer market at 16:00
(https://norges-bank.no/en/topics/Statistics/norwegian-government-securities/generiske-statsrenter).
An effective yield compounds annually on actual/365, as Norges Bank's
Treasury bill terms state it, R = ((100/K)^(365/d) - 1) x 100
(https://www.norges-bank.no/globalassets/upload/statsgjeld/2021/vedlegg-til-primarhandleravtale---statskasseveksler-eng.pdf).

**Zero-coupon curve** (`norgesbank_curves` too, `GOVT_ZEROCOUPON`). The
zero-coupon government curve, one `rate_curve` record, its points from 6
months to 10 years each a `zero` rate at its tenor, estimated by the
Nelson-Siegel-Svensson method, the integral of its forward-rate function
(https://www.norges-bank.no/contentassets/6bf78dd3f9934e89818acdd23f95b1e2/zero-coupon-yields.pdf),
recorded continuously compounded on actual/365 -- the plugin's statement of
that form; Norges Bank names no compounding.

**FX** (`norgesbank_fx`, `EXR`, `B.<currency>.NOK.SP`): each currency's
daily rate at the ECB's concertation, 14:15 CET, kroner per unit or per
hundred units of the currency as its `UNIT_MULT` states; each recorded per
one unit, the hundreds divided by 100 exactly, a `Price` of the currency's
cash instrument in Norwegian kroner, never inverted. The two krone indices
(`I44`, `TWI`) and the SDR (`XDR`) are **not carried**: no currency's cash.

Each record is asked of the deployment by its code proposed here as a
`symbol` at the source `norgesbank`, a name **proposed** with this version
for the platform's seed; the platform seeds none yet, so until a deployment
holds a record its values wait, reported missing, never minted. Each
currency is resolved by its ISO 4217 code, as plugin-ecb resolves its.
"""

from __future__ import annotations

from dataclasses import dataclass

from meridian.operations import RateConvention
from meridian.roles.data import rates

SOURCE = "norgesbank"
INTEREST_RATE, INDEX, RATE_CURVE = "interest_rate", "index", "rate_curve"

#: The krone money market's convention; an effective yield's; a zero rate's.
MONEY_MARKET_365 = RateConvention(day_count="act_365_fixed", compounding="simple")
EFFECTIVE = RateConvention(day_count="act_365_fixed", compounding="compounded", periods_per_year=1)
CONTINUOUS = rates.CONTINUOUS
NOWA_INDEX_BASE = "2020-01-02=100"


@dataclass(frozen=True)
class Record:
    """A referential record, by the code proposed for it at `norgesbank`."""

    code: str
    instrument_type: str
    description: str

    @property
    def identifier(self) -> tuple[str, str, str]:
        return ("symbol", self.code, SOURCE)


NOWA_RECORD = Record("NOWA", INTEREST_RATE, "Norwegian Overnight Weighted Average (NOWA)")
NOWA_INDEX_RECORD = Record("NOWA compounded index", INDEX, "Nowa compounded index (Nowai)")
POLICY_RECORD = Record("Policy rate", INTEREST_RATE, "Norges Bank policy rate")
GENERIC_RECORD = Record(
    "Generic yields", RATE_CURVE, "Norwegian government securities' generic yields"
)
ZERO_RECORD = Record("Zero coupon yields", RATE_CURVE, "Norwegian government zero coupon yields")
RECORDS = (NOWA_RECORD, NOWA_INDEX_RECORD, POLICY_RECORD, GENERIC_RECORD, ZERO_RECORD)

#: The series read, by the key each states, and what each is.
NOWA = "NOWA.ON.R"
NOWA_TRANSACTIONS = "NOWA.ON.T"
NOWA_INDEX = "NOWA.1D.I"
POLICY = "KPRA.SD.R"
#: Each rate series: its record and kind.
RATE_KINDS = {
    NOWA: (NOWA_RECORD, "fixing"),
    NOWA_INDEX: (NOWA_INDEX_RECORD, "index_level"),
    POLICY: (POLICY_RECORD, "fixing"),
}
#: What Norges Bank publishes beside them and is not carried, and why.
NOT_CARRIED = {
    "NOWA.ON.V": "NOWA's volume: Norges Bank states no unit for it",
    "NOWA.ON.BL, NOWA.ON.BB": "the banks lending and borrowing: no field for them",
    "KPRA.OL.R, KPRA.RR.R": "the overnight lending and reserve rates: not carried in this version",
    "I44, TWI": "the krone's indices: a DerivedSeries, not carried in this version",
    "XDR": "the SDR: a basket, no currency's cash",
}
#: The currencies and indices not carried from EXR.
NOT_CURRENCIES = {"I44", "TWI", "XDR"}
#: The currency every rate is stated in.
KRONE = "NOK"


def tenor_of(stated: str) -> str:
    """A tenor as Norges Bank states it, as the SDK reads one: `12M` stays
    `12M`, `3Y` `3Y`."""
    return stated.strip().upper()
