# Setup

## Launching it

Norges Bank's data need no key and no account. Launch the plugin and approve
its one role, `data`. It reads Norges Bank's values at once, and every hour
after.

Its settings: the **Raw responses window** and **past the window** (the
SDK's), and on a deployment installed for development, **Sample data**:
Norges Bank's answers recorded on 19 November 2026, committed with the
plugin.

## Its datasets

On the deployment's **Data sources** page (deployment admins), for each of
`<instance>:norgesbank_rates`, `<instance>:norgesbank_curves` and
`<instance>:norgesbank_fx`:

1. **License it.** Each dataset describes Norges Bank's terms in words and
   declares no licence ([terms](terms.md)). Norges Bank allows copies with
   it quoted as the source and no change to the content: its derived-use
   setting is where that condition sits. Until a licence is set, the lake
   keeps the rows and reads every use right restrictively.
2. **Entitle** each plugin that reads it.
3. **Priority**, where another dataset states the same values.

## The records

NOWA, its index, the policy rate and the two curves are each about a record
named by a code at `norgesbank`: `norgesbank:NOWA`,
`norgesbank:NOWA compounded index`, `norgesbank:Policy rate`,
`norgesbank:Generic yields`, `norgesbank:Zero coupon yields`. The platform
does not seed them yet, and the plugin never makes one: the Datasets page's
Records tab shows each as not held, and its values wait until your
deployment holds it. Each currency is found by its ISO 4217 code.
