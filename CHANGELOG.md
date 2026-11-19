# Changelog

## 0.1.0

On open-meridian 0.36.0, contract 30, on core aae501d's harness. The
product owner's items 128, 130 and 131 (2026-11-19): Tier 1. The dataset
keys, the records' codes and the source `norgesbank` are proposed here, the
product owner's to approve.

- **`norgesbank_rates`** (push and pull): NOWA, a daily `fixing` with its
  transactions, actual/365 simple as Norges Bank publishes it; the Nowa
  compounded index, an `index_level` based 2 January 2020 = 100; the policy
  rate, a `fixing`, actual/365 simple, the plugin's statement. NOWA's
  volume is not carried: Norges Bank states no unit for it.
- **`norgesbank_curves`** (push and pull): the generic yields, each a
  `benchmark_yield` (ruling 130) at its tenor, effective (annual,
  actual/365); the zero-coupon curve, `zero` points from 6 months to 10
  years, continuously compounded, the plugin's statement. No forwards or
  curve parameters (ruling 131).
- **`norgesbank_fx`** (push and pull): the daily rates against the krone,
  each the `close` price of the currency's cash instrument in kroner per
  one unit, a rate stated per hundred divided exactly.
- **No record minted;** no published time (Norges Bank states none on a
  value).
- **Terms in words** (`declared.TERMS`): quoted as source, no change to the
  content.
- **Pages:** the data role's Connection (with Sources) and Datasets (with
  Records).
- **Sample data:** Norges Bank's answers as received on 2026-11-19.
