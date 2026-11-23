# Citations

Public documentation consulted for the SPECIFIED rules, with verbatim
quotes. Accessed 24 Nov 2026. Each entry notes whether the code
agrees, and where it diverges the pack follows the code.

## S-01 — Peer protocol: IANA port 2459, older servers use 51235

Source: https://xrpl.org/docs/concepts/networks-and-servers/peer-protocol
(XRPL.org peer-protocol documentation.)

> "IANA has assigned port 2459 for the XRP Ledger peer protocol, and you can configure which port(s) your server uses in the xrpld.cfg file. The example config file now listens for incoming peer protocol connections on port 2459 on all network interfaces. Older servers may use the previous port 51235, so you might see peers on either port."

Cross-check: agrees with the code defaults — the default bootstrap
pools use port 51235 (`OverlayImpl.cpp:490-515`, E31). The docs
figure is a deployment statement, not a code fact. Rule R-39,
claim C-17.

## S-02 — Peer protocol: deleting the databases creates a new node key pair

Source: https://xrpl.org/docs/concepts/networks-and-servers/peer-protocol
(same page as S-01.)

> "If you delete the server's databases, it creates a new node key pair, effectively coming online with a different identity."

Cross-check: the code has no counter to this — a node key pair is
generated when none is stored, so a fresh identity follows a
database wipe. The docs statement is a deployment fact, not a code
fact. Rule R-40, finding F-05.

## S-03 — Peer protocol: all peers are treated as untrusted unless clustered

Source: https://xrpl.org/docs/concepts/networks-and-servers/peer-protocol
(same page as S-01.)

> "To participate in the XRP Ledger, xrpld servers connect to arbitrary peers using the peer protocol. (All peers are treated as untrusted, unless they are clustered with the current server.)"

Cross-check: agrees with the code — the handshake verifies a
session signature and a secp256k1 node key (R-24, R-27), which
proves key possession, not trustworthiness; only fixed and
reserved (cluster) slots bypass the caps (R-18). Rule R-42,
claim C-18.

## S-04 — Gnutella revised ping/pong: cache pongs, send only the best N

Source: http://rfc-gnutella.sourceforge.net/src/pong-caching.html
(Gnutella revised ping/pong scheme; the in-repo peerfinder README
cites this document as the inspiration for PeerFinder endpoint
gossip.)

> "The key idea is to cache pongs and send only the best N pongs to a client."

Cross-check: the code matches the shape — endpoint gossip keeps a
livecache of the best recent endpoints, broadcasts at most 12 per
message, and rate-limits acceptance to once per 151 seconds per
peer (R-36, R-37). The docs statement is a design description, not
a code fact. Rule R-41.
