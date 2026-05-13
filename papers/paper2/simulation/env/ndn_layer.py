"""
ndn_layer.py
============
Named Data Networking (NDN) protocol simulation layer.

Components:
  - ContentStore (CS): TTL-based cache with LRU eviction fallback
  - PendingInterestTable (PIT): tracks outstanding Interest packets
  - ForwardingInformationBase (FIB): forwarding table
  - NDNNode: combines CS + PIT + FIB for a single node
  - Packet classes: Interest, Data

Content naming: /vehicle/{vid}/content/{ctype}/{version}
"""

import math
import time
import random
from collections import OrderedDict, defaultdict
from typing import Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Packet Definitions
# ─────────────────────────────────────────────────────────────────────────────
class InterestPacket:
    """NDN Interest packet."""
    def __init__(self, name: str, requester_id: str,
                 timestamp: float, nonce: int = None,
                 timeout_s: float = 4.0):
        self.name        = name
        self.requester   = requester_id
        self.timestamp   = timestamp
        self.nonce       = nonce if nonce is not None else random.randint(0, 2**32)
        self.timeout_s   = timeout_s
        self.hop_count   = 0

    def is_expired(self, current_time: float) -> bool:
        return current_time - self.timestamp > self.timeout_s

    def __repr__(self):
        return f"Interest({self.name}, req={self.requester})"


class DataPacket:
    """NDN Data packet (content object)."""
    def __init__(self, name: str, content_type: int, version: int,
                 producer_id: str, generation_time: float,
                 size_bytes: int = 1500, data: bytes = None):
        self.name            = name
        self.content_type    = content_type
        self.version         = version
        self.producer_id     = producer_id
        self.generation_time = generation_time   # when content was generated
        self.rx_time         = None              # when this node received it
        self.size_bytes      = size_bytes
        self.data            = data

    @property
    def freshness(self) -> Optional[float]:
        """Time since content was generated (seconds). None if rx_time unknown."""
        if self.rx_time is not None:
            return self.rx_time - self.generation_time
        return None

    def __repr__(self):
        return f"Data({self.name}, gen={self.generation_time:.1f})"


# ─────────────────────────────────────────────────────────────────────────────
# Content Store (CS)
# ─────────────────────────────────────────────────────────────────────────────
class ContentStore:
    """
    LRU + TTL content cache.
    TTL can be set per-content or globally.
    """

    def __init__(self, max_size: int = 50, default_ttl_s: float = 30.0):
        self.max_size     = max_size
        self.default_ttl  = default_ttl_s
        # OrderedDict: name → (DataPacket, ttl_s, insert_time)
        self._cache: OrderedDict = OrderedDict()

        # Statistics
        self.total_requests = 0
        self.cache_hits     = 0
        self.cache_misses   = 0

    # ── Lookup ────────────────────────────────────────────────────────────────
    def lookup(self, name: str, current_time: float) -> Optional[DataPacket]:
        """
        Look up content by name. Returns DataPacket if valid (not expired).
        Updates LRU order on hit.
        """
        self.total_requests += 1

        if name not in self._cache:
            self.cache_misses += 1
            return None

        pkt, ttl_s, insert_time = self._cache[name]

        # Check TTL expiry
        if current_time - insert_time > ttl_s:
            # Expired → remove
            del self._cache[name]
            self.cache_misses += 1
            return None

        # Hit: move to most-recently-used end
        self._cache.move_to_end(name)
        self.cache_hits += 1
        return pkt

    # ── Insert ────────────────────────────────────────────────────────────────
    def insert(self, pkt: DataPacket, current_time: float,
               ttl_s: float = None) -> bool:
        """
        Insert a DataPacket into the cache.
        Returns True if inserted (may evict LRU entry if full).
        """
        if ttl_s is None:
            ttl_s = self.default_ttl

        # Already cached (fresher version check)
        if pkt.name in self._cache:
            old_pkt, _, _ = self._cache[pkt.name]
            if old_pkt.generation_time >= pkt.generation_time:
                return False  # Already have a fresher or equal version
            del self._cache[pkt.name]

        # Evict LRU if full
        while len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)  # remove oldest (LRU)

        self._cache[pkt.name] = (pkt, ttl_s, current_time)
        self._cache.move_to_end(pkt.name)
        return True

    # ── Evict ─────────────────────────────────────────────────────────────────
    def evict(self, name: str) -> bool:
        """Explicitly evict an entry."""
        if name in self._cache:
            del self._cache[name]
            return True
        return False

    def evict_expired(self, current_time: float) -> int:
        """Remove all expired entries. Returns count removed."""
        expired = [n for n, (p, ttl, ins) in self._cache.items()
                   if current_time - ins > ttl]
        for n in expired:
            del self._cache[n]
        return len(expired)

    # ── Properties ────────────────────────────────────────────────────────────
    @property
    def size(self) -> int:
        return len(self._cache)

    @property
    def hit_ratio(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests

    def update_ttl(self, name: str, new_ttl: float) -> bool:
        """Update TTL for an existing cache entry."""
        if name in self._cache:
            pkt, _, ins_t = self._cache[name]
            self._cache[name] = (pkt, new_ttl, ins_t)
            return True
        return False

    def get_aoi(self, name: str, current_time: float) -> Optional[float]:
        """Return AoI for cached content, or None if not cached."""
        if name not in self._cache:
            return None
        pkt, ttl_s, insert_time = self._cache[name]
        if current_time - insert_time > ttl_s:
            return None  # expired
        return current_time - pkt.generation_time

    def __repr__(self):
        return (f"ContentStore(size={self.size}/{self.max_size}, "
                f"CHR={self.hit_ratio:.3f})")


# ─────────────────────────────────────────────────────────────────────────────
# Pending Interest Table (PIT)
# ─────────────────────────────────────────────────────────────────────────────
class PendingInterestTable:
    """
    PIT tracks outstanding Interest packets awaiting Data responses.
    Maps: content_name → list of (interface_id, InterestPacket)
    """

    def __init__(self, timeout_s: float = 8.0):
        self.timeout_s = timeout_s
        # name → {nonce: (interface_id, InterestPacket)}
        self._table: Dict[str, Dict[int, Tuple[str, InterestPacket]]] = defaultdict(dict)

    def add_interest(self, interest: InterestPacket, interface_id: str) -> bool:
        """
        Add incoming Interest to PIT.
        Returns True if this is a new entry (first Interest for this name).
        Returns False if aggregate (existing Interest for same name → suppress forwarding).
        """
        name = interest.name
        existing = self._table[name]
        is_new = len(existing) == 0
        existing[interest.nonce] = (interface_id, interest)
        return is_new  # True → forward; False → aggregate (suppress)

    def has_pending(self, name: str, current_time: float) -> bool:
        """Check if there's a non-expired pending Interest for this name."""
        if name not in self._table:
            return False
        entries = self._table[name]
        valid = {nc: (iface, pkt) for nc, (iface, pkt) in entries.items()
                 if not pkt.is_expired(current_time)}
        if not valid:
            del self._table[name]
            return False
        self._table[name] = valid
        return True

    def consume(self, name: str, current_time: float
                ) -> List[Tuple[str, InterestPacket]]:
        """
        Consume PIT entries for `name` (Data arrived).
        Returns list of (interface_id, InterestPacket) to forward Data back to.
        Removes entries from PIT.
        """
        if name not in self._table:
            return []
        entries = self._table.pop(name)
        return [(iface, pkt) for nc, (iface, pkt) in entries.items()
                if not pkt.is_expired(current_time)]

    def cleanup_expired(self, current_time: float) -> int:
        """Remove expired PIT entries. Returns count removed."""
        count = 0
        expired_names = []
        for name, entries in self._table.items():
            valid = {nc: v for nc, v in entries.items()
                     if not v[1].is_expired(current_time)}
            if not valid:
                expired_names.append(name)
            else:
                self._table[name] = valid
            count += len(entries) - len(valid)
        for n in expired_names:
            del self._table[n]
        return count

    @property
    def size(self) -> int:
        return sum(len(v) for v in self._table.values())

    def __repr__(self):
        return f"PIT(entries={self.size})"


# ─────────────────────────────────────────────────────────────────────────────
# Forwarding Information Base (FIB)
# ─────────────────────────────────────────────────────────────────────────────
class ForwardingInformationBase:
    """
    FIB maps name prefixes to next-hop interface IDs with AoI-aware cost.
    """

    def __init__(self):
        # prefix → [(interface_id, cost, aoi_estimate)]
        self._table: Dict[str, List[Tuple[str, float, float]]] = {}

    def add_route(self, prefix: str, interface_id: str,
                  cost: float = 1.0, aoi_estimate: float = 0.0):
        """Add or update a route."""
        if prefix not in self._table:
            self._table[prefix] = []
        # Remove existing entry for same interface
        self._table[prefix] = [(i, c, a) for i, c, a in self._table[prefix]
                                if i != interface_id]
        self._table[prefix].append((interface_id, cost, aoi_estimate))
        # Sort by cost (ascending)
        self._table[prefix].sort(key=lambda x: x[1])

    def update_aoi(self, prefix: str, interface_id: str, aoi: float):
        """Update AoI estimate for a specific route."""
        if prefix in self._table:
            updated = []
            for (iface, cost, old_aoi) in self._table[prefix]:
                if iface == interface_id:
                    # AoI-aware cost: lower AoI → prefer this route
                    new_cost = aoi  # use AoI directly as cost
                    updated.append((iface, new_cost, aoi))
                else:
                    updated.append((iface, cost, old_aoi))
            self._table[prefix] = sorted(updated, key=lambda x: x[1])

    def lookup(self, name: str) -> Optional[str]:
        """
        Return best (lowest-cost) next-hop interface for a name.
        Uses longest-prefix matching.
        """
        best_iface = None
        best_len   = -1

        for prefix, routes in self._table.items():
            if name.startswith(prefix) and len(prefix) > best_len:
                if routes:
                    best_iface = routes[0][0]  # lowest cost
                    best_len = len(prefix)

        return best_iface

    def lookup_all(self, name: str) -> List[str]:
        """Return all next-hop interfaces (sorted by cost)."""
        for prefix, routes in self._table.items():
            if name.startswith(prefix):
                return [iface for iface, cost, aoi in routes]
        return []

    def remove_route(self, prefix: str, interface_id: str = None):
        """Remove a route (or all routes for prefix)."""
        if prefix not in self._table:
            return
        if interface_id is None:
            del self._table[prefix]
        else:
            self._table[prefix] = [(i, c, a) for i, c, a in self._table[prefix]
                                    if i != interface_id]
            if not self._table[prefix]:
                del self._table[prefix]

    def __repr__(self):
        return f"FIB(prefixes={len(self._table)})"


# ─────────────────────────────────────────────────────────────────────────────
# Content Popularity Model (Zipf)
# ─────────────────────────────────────────────────────────────────────────────
class ZipfContentModel:
    """Generates content request names following Zipf distribution."""

    def __init__(self, num_contents: int = 200, alpha: float = 1.0,
                 seed: int = 42):
        self.num_contents = num_contents
        self.alpha        = alpha
        self._rng         = random.Random(seed)

        # Precompute Zipf probabilities
        weights = [1.0 / (i ** alpha) for i in range(1, num_contents + 1)]
        total   = sum(weights)
        self._probs = [w / total for w in weights]
        self._cdf   = []
        cum = 0.0
        for p in self._probs:
            cum += p
            self._cdf.append(cum)

    def sample_content(self) -> int:
        """Return a content index (0-based) sampled from Zipf distribution."""
        r = self._rng.random()
        # Binary search in CDF
        lo, hi = 0, len(self._cdf) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if self._cdf[mid] < r:
                lo = mid + 1
            else:
                hi = mid
        return lo

    def popularity(self, content_id: int) -> float:
        """Return probability of content_id being requested."""
        if 0 <= content_id < self.num_contents:
            return self._probs[content_id]
        return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# NDN Node
# ─────────────────────────────────────────────────────────────────────────────
class NDNNode:
    """
    A single NDN node (vehicle or RSU) with CS, PIT, and FIB.
    """

    def __init__(self, node_id: str, cache_size: int = 50,
                 default_ttl_s: float = 30.0,
                 interest_timeout_s: float = 4.0,
                 pit_timeout_s: float = 8.0,
                 is_rsu: bool = False):
        self.node_id = node_id
        self.is_rsu  = is_rsu

        self.cs  = ContentStore(cache_size, default_ttl_s)
        self.pit = PendingInterestTable(pit_timeout_s)
        self.fib = ForwardingInformationBase()

        self.interest_timeout_s = interest_timeout_s

        # Pending outgoing interests (for AoI computation)
        # content_name → generation_time of last received Data
        self._last_received: Dict[str, float] = {}
        self._content_request_time: Dict[str, float] = {}

        # Position (updated by SUMO env)
        self.x = 0.0
        self.y = 0.0

    def distance_to(self, other: "NDNNode") -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

    # ── Interest Processing ───────────────────────────────────────────────────
    def process_interest(self, interest: InterestPacket,
                         incoming_iface: str,
                         current_time: float
                         ) -> Tuple[Optional[DataPacket], Optional[str]]:
        """
        Process incoming Interest.
        Returns:
          (DataPacket, None)  → CS hit, send Data back
          (None, next_iface)  → forward Interest to next_iface
          (None, None)        → aggregate (PIT already has this), drop
        """
        # CS lookup
        data = self.cs.lookup(interest.name, current_time)
        if data is not None:
            # Cache hit: return Data directly
            data.rx_time = current_time
            return data, None

        # PIT lookup (aggregate if pending)
        is_new = self.pit.add_interest(interest, incoming_iface)
        if not is_new:
            # Aggregated: suppress forwarding
            return None, None

        # FIB lookup: forward Interest
        next_iface = self.fib.lookup(interest.name)
        self._content_request_time[interest.name] = current_time
        return None, next_iface

    # ── Data Processing ───────────────────────────────────────────────────────
    def process_data(self, data: DataPacket,
                     current_time: float,
                     ttl_s: float = None,
                     do_cache: bool = True
                     ) -> List[Tuple[str, DataPacket]]:
        """
        Process incoming Data packet.
        - Optionally cache in CS
        - Satisfy pending PIT entries
        Returns: list of (interface_id, DataPacket) to forward Data back
        """
        data.rx_time = current_time
        self._last_received[data.name] = current_time

        # Cache the data
        if do_cache:
            self.cs.insert(data, current_time, ttl_s)

        # Satisfy PIT
        ifaces = self.pit.consume(data.name, current_time)
        return [(iface, data) for iface, pkt in ifaces]

    # ── AoI ───────────────────────────────────────────────────────────────────
    def get_aoi(self, content_name: str, current_time: float) -> float:
        """
        NDN-aware AoI for a specific content.
        Uses cached version if available; otherwise uses last received time.
        """
        # Check CS first
        cached_aoi = self.cs.get_aoi(content_name, current_time)
        if cached_aoi is not None:
            return cached_aoi

        # Use last received
        if content_name in self._last_received:
            return current_time - self._last_received[content_name]

        # Never received → infinite AoI (cap at large value)
        return 1e6

    # ── Optimal TTL (Theorem 2) ───────────────────────────────────────────────
    @staticmethod
    def optimal_ttl(lambda_k: float, w_k: float,
                    c_miss: float, mu_k: float) -> float:
        """
        Theorem 2: TTL*_k = (1/lambda_k) * ln(1 + w_k*lambda_k/(c_miss*mu_k))
        lambda_k : content update rate (Hz)
        w_k      : AoI weight for content k
        c_miss   : cost of cache miss
        mu_k     : request rate for content k (Hz)
        """
        if lambda_k <= 0 or mu_k <= 0 or c_miss <= 0:
            return 30.0  # default fallback
        val = 1.0 + (w_k * lambda_k) / (c_miss * mu_k)
        ttl = (1.0 / lambda_k) * math.log(max(val, 1.0 + 1e-9))
        return max(ttl, 0.1)  # at least 0.1 s

    def __repr__(self):
        return f"NDNNode({self.node_id}, CS={self.cs}, PIT={self.pit})"


# ─────────────────────────────────────────────────────────────────────────────
# NDN Network Manager
# ─────────────────────────────────────────────────────────────────────────────
class NDNNetwork:
    """
    Manages all NDN nodes (vehicles + RSUs) and inter-node messaging.
    """

    def __init__(self, cache_size: int = 50, num_contents: int = 200,
                 zipf_alpha: float = 1.0, content_update_rate: float = 0.5,
                 default_ttl_s: float = 30.0, seed: int = 42):
        self.cache_size           = cache_size
        self.num_contents         = num_contents
        self.zipf_alpha           = zipf_alpha
        self.content_update_rate  = content_update_rate
        self.default_ttl_s        = default_ttl_s
        self.seed                 = seed

        self._rng  = random.Random(seed)
        self.nodes: Dict[str, NDNNode] = {}

        # Content popularity model
        self.zipf = ZipfContentModel(num_contents, zipf_alpha, seed)

        # Content versions (updated at content_update_rate)
        self._content_versions: Dict[int, int]      = defaultdict(int)
        self._content_gen_times: Dict[int, float]   = defaultdict(float)

        # Global statistics
        self.total_cache_hits   = 0
        self.total_cache_misses = 0
        self.total_tx           = 0
        self.total_tx_success   = 0

    def add_node(self, node_id: str, is_rsu: bool = False,
                 x: float = 0.0, y: float = 0.0) -> NDNNode:
        node = NDNNode(node_id, self.cache_size, self.default_ttl_s,
                       is_rsu=is_rsu)
        node.x = x
        node.y = y
        self.nodes[node_id] = node
        return node

    def remove_node(self, node_id: str):
        self.nodes.pop(node_id, None)

    def update_node_position(self, node_id: str, x: float, y: float):
        if node_id in self.nodes:
            self.nodes[node_id].x = x
            self.nodes[node_id].y = y

    def update_fib(self, current_time: float):
        """
        Rebuild FIBs based on current node positions and AoI estimates.
        For each node, add routes to all reachable nodes.
        """
        node_list = list(self.nodes.values())
        for node in node_list:
            # Clear old FIB
            node.fib._table.clear()
            for other in node_list:
                if other.node_id == node.node_id:
                    continue
                d = node.distance_to(other)
                # V2V range: 300m, V2I range: 500m
                max_range = 500.0 if other.is_rsu else 300.0
                if d <= max_range:
                    prefix = f"/vehicle/{other.node_id}/"
                    # AoI-aware cost: prioritise nodes with fresh content
                    aoi_est = current_time  # will be updated per-content
                    node.fib.add_route(prefix, other.node_id,
                                       cost=d, aoi_estimate=aoi_est)
            # Add catch-all route to RSUs
            rsus = [n for n in node_list if n.is_rsu]
            for rsu in rsus:
                d = node.distance_to(rsu)
                if d <= 500.0:
                    node.fib.add_route("/", rsu.node_id,
                                       cost=d + 0.1, aoi_estimate=0.0)

    def update_content_versions(self, current_time: float, dt: float):
        """
        Stochastically update content versions based on content_update_rate.
        """
        for ctype in range(self.num_contents):
            # Poisson process: P(update in dt) = 1 - exp(-lambda*dt)
            p_update = 1.0 - math.exp(-self.content_update_rate * dt)
            if self._rng.random() < p_update:
                self._content_versions[ctype] += 1
                self._content_gen_times[ctype] = current_time

    def make_content_name(self, producer_id: str, ctype: int) -> str:
        version = self._content_versions[ctype]
        return f"/vehicle/{producer_id}/content/{ctype}/{version}"

    def get_cache_hit_ratio(self) -> float:
        total = self.total_cache_hits + self.total_cache_misses
        return self.total_cache_hits / max(1, total)
