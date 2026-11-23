# Claim-to-evidence index

Every claim in this pack, its status, and the exact evidence for it.
Status meanings: VERIFIED — read from the pinned source with a
grep-verified file:line citation; SPECIFIED — stated in the cited public
documentation and cross-checked against code; MODELLED — an output of
the deterministic simulator on the stated inputs; UNTESTABLE — not
decidable from the pinned source alone.

| Claim | Status | Claim | Evidence |
| --- | --- | --- | --- |
| C-01 | VERIFIED | Default outPeers is 10 (calcOutPeers, maxPeers 21). | R-01, R-02, R-03, E01, E02, E04: `src/xrpld/peerfinder/detail/Tuning.h:52-63`, `PeerfinderConfig.cpp:35-42`. |
| C-02 | VERIFIED | Default inPeers is 11. | R-05, E08: `PeerfinderConfig.cpp:102-112`. |
| C-03 | VERIFIED | ipLimit is 2 per public IP, inbound only. | R-13, R-14, E05, E09: `PeerfinderConfig.cpp:44-62`, `Logic.h:274-285`. |
| C-04 | VERIFIED | One attacker IP with 10 ports can take all outbound slots. | R-14, R-15, R-43, E09, E10: `Logic.h:274-294`; model run S-01 A. |
| C-05 | VERIFIED | No subnet or prefix diversity check exists. | Absence grep: `diversity` 0 hits, `subnet` 0 hits in `src/xrpld/overlay` and `src/xrpld/peerfinder` (probe I-01). |
| C-06 | VERIFIED | Fixed and reserved slots bypass all caps. | R-18, E21: `Counts.h:77-78`. |
| C-07 | VERIFIED | Duplicate endpoint and duplicate key are both rejected. | R-15, R-16, E10, E12: `Logic.h:287-294`, `Logic.h:416-419`. |
| C-08 | VERIFIED | Self-connection is rejected by address and by key. | R-17, E11, E38: `Logic.h:378-393`, `Handshake.cpp:322-323`. |
| C-09 | VERIFIED | The handshake binds the TLS session to the node key (finished-message XOR plus signature). | R-23, R-24, E32, E37: `Handshake.cpp:125-160`, `Handshake.cpp:311-319`. |
| C-10 | VERIFIED | Clock skew over 20 seconds is rejected. | R-26, E35: `Handshake.cpp:252-278`. |
| C-11 | VERIFIED | A full peer answers HTTP 503 with up to 10 redirect endpoints. | R-21, E30: `OverlayImpl.cpp:352-372`. |
| C-12 | VERIFIED | Livecache entries live 30 seconds; endpoint acceptance is rate-limited to once per 151 seconds per peer. | R-37, R-36, E17, E19: `Logic.h:698-712`, `Logic.h:789-823`. |
| C-13 | VERIFIED | Large send queues evict the peer after 4 x 60 second intervals. | R-31, R-32, E40, E41: `PeerImp.cpp:728-762`, `PeerImp.cpp:2590-2600`, overlay `Tuning.h:44-58`. |
| C-14 | VERIFIED | Diverged outbound peers are evicted after 300 seconds, unknown after 600 seconds. | R-31, E40, E43: `PeerImp.cpp:728-762`, `Config.h:296-301`. |
| C-15 | VERIFIED | Redirect IPs enter the bootcache unchecked, at most 30. | R-21, E30: `Logic.h:1274-1280` (read from source; no excerpt file for this range), `OverlayImpl.cpp:352-372`. |
| C-16 | VERIFIED | The bootcache holds at most 1000 entries and prunes the 10 percent lowest valence. | R-12, E25: `Bootcache.cpp:225-250`. |
| C-17 | SPECIFIED | IANA assigned port 2459 for the peer protocol; older servers use 51235. | R-39, `docs/citations.md` S-01: peer-protocol documentation, 24 Nov 2026. |
| C-18 | SPECIFIED | All peers are treated as untrusted unless clustered. | R-42, `docs/citations.md` S-03: peer-protocol documentation, 24 Nov 2026. |
| C-19 | MODELLED | With no fixed peers, 1 attacker IP x 10 ports eclipses a fresh victim. | R-43; scenario S-01 run A; `outputs/derived/overlay-eclipse-results.json`. |
| C-20 | MODELLED | 2 fixed honest peers keep a victim degraded, not eclipsed, under the same attack. | Scenario S-01 run B; `outputs/derived/overlay-eclipse-results.json`. |
| C-21 | MODELLED | Total honest loss partitions the victim; rejoin takes 2 rounds. | R-44; scenarios S-09, S-10; `outputs/derived/overlay-eclipse-results.json`. |
| C-22 | MODELLED | 6 reserved honest peers keep a victim connected under a 5-IP Sybil flood. | Scenario S-05 run B; `outputs/derived/overlay-eclipse-results.json`. |
| C-23 | UNTESTABLE | Live-network eclipse resistance against a botnet with distinct public IPs. | R-45; no live node was run (gap G-01). |
| C-24 | UNTESTABLE | Real-world churn rates and honest-peer availability. | No live measurement (gap G-02). |
