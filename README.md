# meridian-norges-bank

Norges Bank's public rates for [Open Meridian](https://open-meridian.com): an
Open Meridian plugin that puts NOWA and its compounded index, the policy
rate, the Norwegian government securities' generic yields, the zero-coupon
curve and the daily exchange rates against the krone into a deployment's
lake. It reads Norges Bank's open data API (SDMX) and holds the `data` role,
a data plugin. This is release 0.1.0, a draft for the product owner. How to
set it up and use it is in [docs/](docs/README.md).

It is built on the SDK it pins, `open-meridian==0.37.0` (contract 30).

## What it records

Each dataset is pushed as Norges Bank publishes it, and any past day pulled
when the lake wants it.

- **`<instance>:norgesbank_rates`**: NOWA, each day's `fixing` with its
  number of transactions, actual/365 simple, as Norges Bank publishes it;
  the Nowa compounded index, an index level based 2 January 2020 = 100; the
  policy rate, a `fixing`, actual/365 simple (the plugin's statement, since
  Norges Bank states only per cent).
- **`<instance>:norgesbank_curves`**: the generic yields -- "the effective
  yield on the government security closest to the stated maturity", bills
  at 3, 6 and 12 months and bonds at 3, 5, 7 and 10 years -- each a
  `benchmark_yield` at its tenor on one curve record, an effective yield,
  annual on actual/365 as Norges Bank's bill terms state it; and the
  zero-coupon curve, `zero` rates from 6 months to 10 years, recorded
  continuously compounded (the plugin's statement of the NSS form; Norges
  Bank names no compounding). No forward rates and no curve parameters.
- **`<instance>:norgesbank_fx`**: each currency's daily rate against the
  krone, the price of the currency's cash instrument in kroner per one
  unit: a rate Norges Bank states per hundred units is divided by 100,
  exactly.
- **Records:** NOWA, its index, the policy rate and the two curves are each
  asked of the deployment by a code at `norgesbank` (`norgesbank:NOWA`);
  the platform seeds none yet, so each is reported missing, never minted,
  and its rates wait. Each currency resolves by its ISO 4217 code.
- **Not presented:** NOWA's volume (Norges Bank states no unit for it) and
  its counts of lending and borrowing banks; the overnight lending and
  reserve rates; the krone's indices (I44, TWI) and the SDR; the auctions
  (no operation for an auction result yet). No published time is recorded:
  Norges Bank states none.

## Deploying it

On a deployment, with the `meridian` CLI connected (`meridian connect`):

    meridian plugin upload                   # from this directory
    meridian plugin launch norges-bank       # a deployment admin approves its one role, data

No key and no account. A deployment admin then licenses its three datasets
and entitles the plugins that read them on the Data sources page
([docs/setup.md](docs/setup.md)).

## Checking it

    make ci-local                  # lint, tests, plugin check, image, e2e: the pre-push gate
    make preview SHOTS=<dir>       # each page in a browser with the kit, at 375, 582 and 1280 px

`tests/test_suite.py` runs the SDK's data suite on the plugin's own
conversion, and it passes; a case about what Norges Bank never states here
is not presented, with why.

## The terms, summarised

Not legal advice; read Norges Bank's own words
([disclaimer](https://www.norges-bank.no/en/disclaimer/),
[NOWA FAQ](https://www.norges-bank.no/en/topics/liquidity-and-markets/nowa/faq-nowa/))
before relying on them. Its content may be copied with Norges Bank quoted as
the source and no change to the content; no inline linking; no liability.
NOWA is published free and needs no licence. Commercial use is not
addressed. Each dataset says so in words, and declares no licence: the
deployment admin's licence is the one enforced. This project is not
affiliated with or endorsed by Norges Bank.

## Licence

Apache-2.0 (LICENSE, NOTICE). Norges Bank's answers under
`src/norges_bank/responses/` are as received on 2026-11-19.
