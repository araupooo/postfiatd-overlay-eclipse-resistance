# Scenario matrix

Deterministic outputs of `src/overlay_eclipse_model.py` on
`configs/scenarios.json`. `honest_links = honest_outbound + fixed +
reserved`; connected when honest links are at least 5 (half the
outbound target of 10), degraded at 1-4, eclipsed when honest links
are 0 but the victim is still connected (attacker outbound > 0 or
honest inbound > 0), partitioned when honest links are 0, honest
inbound is 0, and attacker outbound is 0. Partition and churn runs
report the worst phase; recovery rounds are `ceil(refill / 20)` plus
one round when a rejoin follows total honest loss.

| Scenario | Run | Attacker IPs | Attacker ports | Fixed | Reserved | Outcome | Reason | Attacker outbound | Honest outbound | Honest inbound | Honest links | Rounds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S-01 | A | 1 | 10 | 0 | 0 | eclipsed | no_honest_outbound_link_attacker_controls_outbound_view | 10 | 0 | 9 | 0 | 1 |
| S-01 | B | 1 | 10 | 1 | 0 | degraded | honest_links_below_half_outbound_target | 10 | 0 | 9 | 1 | 1 |
| S-02 | A | 5 | 10 | 0 | 0 | eclipsed | no_honest_outbound_link_attacker_controls_outbound_view | 10 | 0 | 1 | 0 | 1 |
| S-02 | B | 5 | 10 | 1 | 0 | degraded | honest_links_below_half_outbound_target | 10 | 0 | 1 | 1 | 1 |
| S-03 | A | 11 | 10 | 0 | 0 | eclipsed | no_honest_outbound_link_attacker_controls_outbound_view | 10 | 0 | 0 | 0 | 1 |
| S-03 | B | 11 | 10 | 1 | 0 | degraded | honest_links_below_half_outbound_target | 10 | 0 | 0 | 1 | 1 |
| S-04 | A | 11 | 10 | 2 | 0 | degraded | honest_links_below_half_outbound_target | 10 | 0 | 0 | 2 | 1 |
| S-05 | A | 5 | 10 | 0 | 3 | degraded | honest_links_below_half_outbound_target | 10 | 0 | 1 | 3 | 1 |
| S-05 | B | 5 | 10 | 0 | 6 | connected | honest_links_at_least_half_outbound_target | 10 | 0 | 1 | 6 | 1 |
| S-06 | A | 0 | 0 | 0 | 0 | connected | honest_links_at_least_half_outbound_target | 0 | 10 | 11 | 10 | 1 |
| S-07 | A | 0 | 0 | 0 | 0 | connected | honest_links_at_least_half_outbound_target | 0 | 8 | 8 | 8 | 1 |
| S-08 | A | 0 | 0 | 0 | 0 | connected | honest_links_at_least_half_outbound_target | 0 | 10 | 11 | 10 | 1 |
| S-09 | A | 0 | 0 | 0 | 0 | partitioned | no_peer_connections_at_all | 0 | 0 | 0 | 0 | 2 |
| S-10 | A | 0 | 0 | 0 | 0 | partitioned | no_peer_connections_at_all | 0 | 0 | 0 | 0 | 2 |
| S-11 | A | 0 | 0 | 1 | 0 | degraded | honest_links_below_half_outbound_target | 0 | 0 | 0 | 1 | 2 |
| S-12 | A | 1 | 10 | 0 | 0 | eclipsed | no_honest_outbound_link_attacker_controls_outbound_view | 10 | 0 | 0 | 0 | 1 |
| S-12 | B | 1 | 10 | 0 | 0 | connected | honest_links_at_least_half_outbound_target | 0 | 10 | 9 | 10 | 1 |
| S-13 | A | 10 | 1 | 0 | 0 | connected | honest_links_at_least_half_outbound_target | 0 | 10 | 11 | 10 | 1 |

Totals: connected 6, degraded 6, eclipsed 4, partitioned 2 (18 runs).

## Eclipse threshold

Attacker endpoints against a fresh victim with 50 honest peers and no
fixed peers. 10 attacker endpoints fill all 10 outbound slots
regardless of IP count: the threshold is endpoints, not IPs.

| Attacker IPs | Attacker ports | Attacker endpoints | Attacker outbound | Attacker inbound | Honest outbound | Honest inbound | Honest links | Outcome |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 1 | 1 | 2 | 9 | 9 | 9 | connected |
| 1 | 5 | 5 | 5 | 2 | 5 | 9 | 5 | connected |
| 1 | 10 | 10 | 10 | 2 | 0 | 9 | 0 | eclipsed |
| 2 | 10 | 20 | 10 | 4 | 0 | 7 | 0 | eclipsed |
| 5 | 2 | 10 | 10 | 10 | 0 | 1 | 0 | eclipsed |
| 5 | 10 | 50 | 10 | 10 | 0 | 1 | 0 | eclipsed |
| 11 | 1 | 11 | 10 | 11 | 0 | 0 | 0 | eclipsed |

## Scenario notes

- S-01 Sybil flood from a single IP: A — Sybil flood, 1 IP x 10 ports, no fixed peers; B — Sybil flood, 1 IP x 10 ports, 1 fixed honest peer
- S-02 Sybil flood from five IPs: A — Sybil flood, 5 IPs x 10 ports, no fixed peers; B — Sybil flood, 5 IPs x 10 ports, 1 fixed honest peer
- S-03 Targeted eclipse of an isolated victim: A — Targeted eclipse, no fixed peers; B — Targeted eclipse, 1 fixed honest peer
- S-04 Targeted eclipse with two fixed peers: A — Targeted eclipse, 2 fixed honest peers
- S-05 Reserved honest peers under Sybil flood: A — 5-IP flood, 3 reserved honest peers; B — 5-IP flood, 6 reserved honest peers
- S-06 Healthy network, no attacker: A — Healthy network, large honest pool
- S-07 Healthy network, small honest pool: A — Healthy network, small honest pool
- S-08 Churn, half the honest peers leave: A — Churn, half the honest peers leave
- S-09 Churn, total honest loss and return: A — Churn, all honest peers leave then return
- S-10 Partition and rejoin, no anchor: A — Partition for 10 rounds, then rejoin
- S-11 Partition and rejoin with a fixed anchor: A — Partition for 10 rounds, 1 fixed peer across the split
- S-12 Redirect poisoning via a full peer: A — Redirect poisoning, fresh node; B — Redirect poisoning, mature node
- S-13 Handshake rejection under attack: A — Handshake rejection of a Sybil flood
