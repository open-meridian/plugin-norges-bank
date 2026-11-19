# Overview

Norges Bank publishes the rates this plugin puts into your deployment's
lake:

- **NOWA, its compounded index and the policy rate**
  (`<instance>:norgesbank_rates`): NOWA each banking day, with its number of
  transactions; the Nowa compounded index, based 2 January 2020 = 100; and
  the policy rate.
- **Curves** (`<instance>:norgesbank_curves`): the generic yields of
  Norwegian government securities, bills at 3, 6 and 12 months and bonds at
  3, 5, 7 and 10 years; and the zero-coupon curve from 6 months to 10 years.
- **Exchange rates** (`<instance>:norgesbank_fx`): each currency's daily
  rate against the krone, the price of one unit of that currency in kroner.

It reads Norges Bank's open data API: no key, no account. It checks for new
values every hour; any past day of any dataset is read when the lake asks
for it.

## What it records

- **Each value as Norges Bank writes it,** made an exact decimal from its
  text. A day Norges Bank states nothing for is no value, never a zero.
- **Conventions.** NOWA and its index are actual/365, as Norges Bank
  publishes them; the policy rate the same, the plugin's statement. The
  generic yields are effective yields, annual on actual/365, as Norges
  Bank's Treasury bill terms state an effective rate. The zero-coupon curve
  is recorded continuously compounded, the plugin's statement of the
  Nelson-Siegel-Svensson form Norges Bank describes; it names no
  compounding.
- **Per one unit.** Norges Bank states some currencies per hundred units
  (the yen, the Swedish krona); each is recorded per one unit, divided by
  100 exactly.
- **Against your deployment's records.** NOWA, its index, the policy rate
  and the two curves are each asked of your deployment by a code at
  `norgesbank`; the plugin never makes a record: one your deployment does
  not hold is reported missing, and its values wait. Each currency is found
  by its ISO 4217 code.
- **No published time:** Norges Bank states none on a value.
- **Not carried:** NOWA's volume (Norges Bank states no unit for it) and its
  counts of banks; the overnight lending and reserve rates; the krone's
  indices and the SDR; the auctions.

## What it never does

It records no trade and shows no value on its pages. It holds no account and
uses no key. Its exchange rates are never inverted.
