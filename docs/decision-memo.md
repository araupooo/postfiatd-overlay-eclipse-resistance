# Operator decision memo

## The one rule that matters

**Set fixed peers.** A fresh node with no fixed peers and no
reservations is eclipsed by a single attacker IP offering 10
distinct ports (scenario S-01 run A). One fixed honest peer turns
that eclipse into a degraded connection (S-01 run B); two fixed
peers hold it degraded under a full targeted eclipse (S-04). Fixed
peers are tried first by autoconnect (R-07) and bypass every slot
cap (R-18). They are the only anchor the code provides, and the
default configuration has none (F-08).

## What to configure

1. **Fixed peers.** Add at least 2 trusted, long-lived peers as
   fixed peers. They bypass the inbound and outbound caps, they
   are tried before livecache and bootcache addresses, and they
   survive a bootcache flush. Do not rely on the 4 default
   bootstrap DNS pools (`r.ripple.com`, `sahyadri.isrdc.in`,
   `hubs.xrpkuwait.com`, `hub.xrpl-commons.org`) — they are a
   first-contact convenience, not an anchor (K-09).
2. **Reserved peers for clusters.** Reserved (cluster) peers also
   bypass all caps (R-18), but there is no bound on the
   reservation count in the code (F-03). Keep the reservation
   list short and audited: every reserved slot is a slot an
   ordinary peer cannot take.
3. **Do not raise maxPeers expecting diversity.** Raising
   maxPeers raises outPeers (15 percent, floored at 10) and
   inPeers together, but there is no subnet or prefix diversity
   check anywhere in peer selection (F-02). More slots just give
   an attacker more slots to fill from one prefix.
4. **Watch the bootcache.** Bootcache valence is local-only and
   resets to -1 on a single failed attempt (R-11), so a popular
   honest hub can be demoted by one failed connection. If a
   trusted hub stops being tried, check its valence before
   assuming it is down.
5. **Clock discipline.** A peer more than 20 seconds off is
   rejected at handshake (R-26). Keep the node clock synced;
   a 21-second skew looks identical to a hostile peer.

## What the code will not do for you

- It will not limit outbound connections per IP. ipLimit (2) is
  checked only for inbound slots (R-14). An attacker needs one
  public IP and 10 ports to own your outbound view.
- It will not check redirect endpoints. Up to 30 redirect IPs
  enter the bootcache unchecked per redirect (R-21). A full peer
  can poison your cache; treat redirect-heavy bootcache entries
  with suspicion.
- It will not tell you whether you are connected. The
  `isConnectedToNetwork` check is dead code (F-11). Monitor
  honest outbound links yourself: fewer than 5 honest outbound
  links means degraded, zero means eclipsed or partitioned.
- It will not slow autoconnect to the documented 10-second
  cadence. `secondsPerConnect` is defined but unused (F-12);
  autoconnect runs on the 1-second overlay timer.

## After a partition

Refilling 10 outbound slots takes 2 autoconnect rounds (R-44):
one batch of up to 20 simultaneous attempts, plus one round for
stale-peer replacement. The persistent bootcache is the only
memory of honest peers after a long partition (livecache entries
live 30 seconds). Do not delete the peerfinder databases after a
partition unless you intend to come back with a new identity —
deleting them creates a new node key pair (R-40) and throws away
the bootcache that would have reconnected you.
