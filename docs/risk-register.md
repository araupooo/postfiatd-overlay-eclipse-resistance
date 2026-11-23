# Risk register

Sybil, eclipse, partition, and liveness risks in the postfiatd peer
overlay. Severity is judged by impact on the node's ability to keep
honest outbound links and to rejoin the network after a partition.

| Risk | Severity | Risk | Evidence / mitigation in the pinned code |
| --- | --- | --- | --- |
| K-01 | HIGH | Single-IP outbound eclipse: one attacker IP with 10 distinct ports fills all 10 default outbound slots. | No per-IP cap on outbound slots (R-14, F-01). Mitigation: fixed peers (R-07) or reserved peers (R-18); scenario S-01. |
| K-02 | HIGH | Prefix-level Sybil fill: many attacker IPs from one prefix fill every slot, with no diversity check to stop them. | No subnet or prefix diversity mechanism exists (F-02); ipLimit is per exact IP only. |
| K-03 | HIGH | Unbounded reservations bypass caps: a misconfigured or compromised cluster reservation table can crowd out ordinary peers. | Reserved slots bypass all caps (R-18) and `PeerReservationTable` has no size limit in the pinned source (F-03). |
| K-04 | MEDIUM | Redirect cache poisoning: a full peer's redirect endpoints enter the bootcache unchecked. | Up to 30 redirect IPs per redirect, no connectivity test (R-21, F-04); scenario S-12. |
| K-05 | MEDIUM | Free Sybil identities: a fresh node key costs nothing, so an attacker can mint identities at will. | The handshake only proves possession of a secp256k1 key (R-24, R-27); deleting the databases creates a new identity (R-40). |
| K-06 | MEDIUM | Bootcache valence demotion of honest hubs: one failed attempt resets a hub's valence to -1. | Valence is local-only and resets on a single failure (R-11, F-06). |
| K-07 | MEDIUM | Endpoint-gossip displacement: attacker entries can displace honest ones in a 64-entry message. | Oversize endpoint messages are sampled at random (R-36, F-07). |
| K-08 | MEDIUM | No default fixed peers: a fresh node with no configuration has no anchor at all. | Fixed peers are config-only; the default configuration has none (R-07, F-08). |
| K-09 | MEDIUM | Bootstrap depends on 4 third-party DNS pools. | Default bootstrap pools are `r.ripple.com`, `sahyadri.isrdc.in`, `hubs.xrpkuwait.com`, `hub.xrpl-commons.org`, all port 51235 (`OverlayImpl.cpp:490-515`, E31). If all four fail, a fresh node has no entry point. |
| K-10 | MEDIUM | Inbound slots fillable at 2 per IP: 6 attacker IPs take all 11 inbound slots. | ipLimit is 2 per public IP (R-13); 6 IPs x 2 = 12 > 11 inbound slots. Honest inbound contact is then closed. |
| K-11 | MEDIUM | Partition during total honest loss; rejoin depends on bootcache freshness. | Livecache entries live 30 s (R-37); the persistent bootcache is the only memory of honest peers after a long partition (scenarios S-09, S-10). |
| K-12 | LOW | 20 second clock rejection of honest skewed peers. | A peer more than 20 s off is rejected even if honest (R-26, F-09). |
| K-13 | LOW | Diverged inbound peers are kept. | Diverged and unknown eviction applies to outbound peers only (R-31, F-10). |
| K-14 | LOW | Dead connectedness signal: the node cannot tell from its own counts whether it is connected to the network. | `isConnectedToNetwork` is never called (F-11); as written it returns false whenever `m_out_max > 0`. |
