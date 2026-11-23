# Gap register

Questions the pinned source alone cannot answer. Each gap is a
source-only limitation: it names what is unknown, why it is unknown,
and what would close it.

| Gap | Gap | Why it is open | What would close it |
| --- | --- | --- | --- |
| G-01 | No live node run; all attack outcomes are simulator outputs. | No live node was run in this pack. | A live node run against a controlled attacker, or a multi-node testnet with hostile peers. |
| G-02 | No measurement of real honest-peer pool sizes or churn rates. | Pool sizes and churn are live-network data, not code. | Live peer logs over weeks, reporting connected-peer counts and churn. |
| G-03 | No subnet or diversity data: the code has no such mechanism to measure against. | The absence is verified by grep, but there is no counterfactual to measure. | A design change adding prefix diversity, then a measurement of its effect. |
| G-04 | Reservation-count bound unknown: the table is unbounded in code, but operator practice is not measured. | `PeerReservationTable` has no size limit; how many reservations real operators configure is deployment data. | A survey of operator configurations, or a code change bounding the table. |
| G-05 | Real redirect-poisoning rate unknown. | Redirect IPs enter the bootcache unchecked (R-21), but how often full peers actually send hostile redirects is live data. | Instrumented redirect logging on a live node. |
| G-06 | `isConnectedToNetwork` dead code: its intended semantics are unclear. | The function is defined but never called; the comment claims a connectedness test the code cannot perform as written. | Reading the commit history for the function's introduction, or asking the maintainers. |
| G-07 | `secondsPerConnect` unused: its intended 10 second cadence is unconfirmed. | The constant is defined in `Tuning.h:40` but never used; autoconnect runs on the 1 second overlay timer instead. | Reading the commit history, or a code change wiring the constant back in. |
| G-08 | IPv6 and CGNAT behaviour of `is_public` untested in this pack. | `IPAddressV4.cpp:38-50` (E44) covers IPv4 ranges; IPv6 and CGNAT handling were not traced. | A read of the IPv6 `is_public` path plus live IPv6 peer data. |
