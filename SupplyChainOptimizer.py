#!/usr/bin/env python3
"""
SupplyChainOptimizer.py
=======================
An educational supply chain optimization tool demonstrating:
  - Dijkstra's shortest path algorithm (implemented from scratch with heapq)
  - Haversine great-circle distance between geographic coordinates
  - Graph-based US logistics network (10 DCs + 30 Retail Stores)
  - Inventory simulation with shortage detection and optimal restocking
  - Interactive map visualization via Folium (saved as HTML)

Real-World Context
------------------
Modern e-commerce platforms (Amazon, Walmart, Target) rely on graph-based
shortest-path optimization to route inventory from distribution centers to
stores or directly to customers.  In conversational commerce AI systems,
a similar "knowledge graph" connects products, warehouses, and stores as
nodes so that an AI assistant can answer "Which warehouse can ship Product X
to the user the fastest?" -- Dijkstra finds the answer in milliseconds.

Requirements
------------
  pip install folium          # for interactive map (optional but recommended)

Usage
-----
  python SupplyChainOptimizer.py
"""

from __future__ import annotations   # allows modern type hints on Python 3.8+

import heapq                          # built-in min-heap (priority queue)
import math                           # for Haversine trig
import random                         # demand / shortage simulation
import os                             # path handling
from collections import defaultdict   # adjacency list initialisation

# -- optional dependency --------------------------------------------------------
try:
    import folium          # pip install folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False
    print("[WARNING] folium not installed -- map visualisation will be skipped.")
    print("          Install it with:  pip install folium\n")


# ==============================================================================
# SECTION 1 -- GEOGRAPHIC DATA
#   10 Distribution Centers at major US logistics hubs
#   30 Retail Stores spread across the country
# ==============================================================================

# Each entry: id, human-readable name, city, state, latitude, longitude.
# Latitude/longitude are approximate real coordinates for each city.

DISTRIBUTION_CENTERS: list[dict] = [
    # id      name                      city             state    lat       lon
    {"id": "DC01", "name": "Los Angeles DC",    "city": "Los Angeles",    "state": "CA", "lat":  34.0522, "lon": -118.2437},
    {"id": "DC02", "name": "Dallas DC",         "city": "Dallas",         "state": "TX", "lat":  32.7767, "lon":  -96.7970},
    {"id": "DC03", "name": "Chicago DC",        "city": "Chicago",        "state": "IL", "lat":  41.8781, "lon":  -87.6298},
    {"id": "DC04", "name": "Atlanta DC",        "city": "Atlanta",        "state": "GA", "lat":  33.7490, "lon":  -84.3880},
    {"id": "DC05", "name": "Phoenix DC",        "city": "Phoenix",        "state": "AZ", "lat":  33.4484, "lon": -112.0740},
    {"id": "DC06", "name": "New York DC",       "city": "New York",       "state": "NY", "lat":  40.7128, "lon":  -74.0060},
    {"id": "DC07", "name": "Seattle DC",        "city": "Seattle",        "state": "WA", "lat":  47.6062, "lon": -122.3321},
    {"id": "DC08", "name": "Houston DC",        "city": "Houston",        "state": "TX", "lat":  29.7604, "lon":  -95.3698},
    {"id": "DC09", "name": "Denver DC",         "city": "Denver",         "state": "CO", "lat":  39.7392, "lon": -104.9903},
    {"id": "DC10", "name": "Miami DC",          "city": "Miami",          "state": "FL", "lat":  25.7617, "lon":  -80.1918},
]

RETAIL_STORES: list[dict] = [
    # -- Pacific Northwest / West Coast --------------------------------------
    {"id": "ST01", "name": "Portland Store",       "city": "Portland",       "state": "OR", "lat":  45.5051, "lon": -122.6750},
    {"id": "ST02", "name": "San Francisco Store",  "city": "San Francisco",  "state": "CA", "lat":  37.7749, "lon": -122.4194},
    {"id": "ST03", "name": "San Diego Store",      "city": "San Diego",      "state": "CA", "lat":  32.7157, "lon": -117.1611},
    {"id": "ST04", "name": "Las Vegas Store",      "city": "Las Vegas",      "state": "NV", "lat":  36.1699, "lon": -115.1398},
    # -- Mountain West --------------------------------------------------------
    {"id": "ST05", "name": "Salt Lake City Store", "city": "Salt Lake City", "state": "UT", "lat":  40.7608, "lon": -111.8910},
    {"id": "ST06", "name": "Albuquerque Store",    "city": "Albuquerque",    "state": "NM", "lat":  35.0844, "lon": -106.6504},
    {"id": "ST07", "name": "Boise Store",          "city": "Boise",          "state": "ID", "lat":  43.6150, "lon": -116.2023},
    # -- Midwest / Great Plains -----------------------------------------------
    {"id": "ST08", "name": "Kansas City Store",    "city": "Kansas City",    "state": "MO", "lat":  39.0997, "lon":  -94.5786},
    {"id": "ST09", "name": "Minneapolis Store",    "city": "Minneapolis",    "state": "MN", "lat":  44.9778, "lon":  -93.2650},
    {"id": "ST10", "name": "Milwaukee Store",      "city": "Milwaukee",      "state": "WI", "lat":  43.0389, "lon":  -87.9065},
    {"id": "ST11", "name": "Omaha Store",          "city": "Omaha",          "state": "NE", "lat":  41.2565, "lon":  -95.9345},
    {"id": "ST12", "name": "St. Louis Store",      "city": "St. Louis",      "state": "MO", "lat":  38.6270, "lon":  -90.1994},
    # -- Great Lakes / Rust Belt ----------------------------------------------
    {"id": "ST13", "name": "Detroit Store",        "city": "Detroit",        "state": "MI", "lat":  42.3314, "lon":  -83.0458},
    {"id": "ST14", "name": "Columbus Store",       "city": "Columbus",       "state": "OH", "lat":  39.9612, "lon":  -82.9988},
    {"id": "ST15", "name": "Indianapolis Store",   "city": "Indianapolis",   "state": "IN", "lat":  39.7684, "lon":  -86.1581},
    {"id": "ST16", "name": "Cleveland Store",      "city": "Cleveland",      "state": "OH", "lat":  41.4993, "lon":  -81.6944},
    {"id": "ST17", "name": "Pittsburgh Store",     "city": "Pittsburgh",     "state": "PA", "lat":  40.4406, "lon":  -79.9959},
    {"id": "ST18", "name": "Cincinnati Store",     "city": "Cincinnati",     "state": "OH", "lat":  39.1031, "lon":  -84.5120},
    # -- South / Southeast ----------------------------------------------------
    {"id": "ST19", "name": "Louisville Store",     "city": "Louisville",     "state": "KY", "lat":  38.2527, "lon":  -85.7585},
    {"id": "ST20", "name": "Nashville Store",      "city": "Nashville",      "state": "TN", "lat":  36.1627, "lon":  -86.7816},
    {"id": "ST21", "name": "Memphis Store",        "city": "Memphis",        "state": "TN", "lat":  35.1495, "lon":  -90.0490},
    {"id": "ST22", "name": "New Orleans Store",    "city": "New Orleans",    "state": "LA", "lat":  29.9511, "lon":  -90.0715},
    {"id": "ST23", "name": "Birmingham Store",     "city": "Birmingham",     "state": "AL", "lat":  33.5207, "lon":  -86.8025},
    {"id": "ST24", "name": "Oklahoma City Store",  "city": "Oklahoma City",  "state": "OK", "lat":  35.4676, "lon":  -97.5164},
    {"id": "ST25", "name": "El Paso Store",        "city": "El Paso",        "state": "TX", "lat":  31.7619, "lon": -106.4850},
    # -- East Coast -----------------------------------------------------------
    {"id": "ST26", "name": "Charlotte Store",      "city": "Charlotte",      "state": "NC", "lat":  35.2271, "lon":  -80.8431},
    {"id": "ST27", "name": "Raleigh Store",        "city": "Raleigh",        "state": "NC", "lat":  35.7796, "lon":  -78.6382},
    {"id": "ST28", "name": "Richmond Store",       "city": "Richmond",       "state": "VA", "lat":  37.5407, "lon":  -77.4360},
    {"id": "ST29", "name": "Philadelphia Store",   "city": "Philadelphia",   "state": "PA", "lat":  39.9526, "lon":  -75.1652},
    {"id": "ST30", "name": "Boston Store",         "city": "Boston",         "state": "MA", "lat":  42.3601, "lon":  -71.0589},
]

# DC-to-DC interstate logistics corridors.
# These model real US highway arteries between major hub cities.
# They allow multi-hop transfers: stock can flow DC_B -> DC_A -> Store
# when geographic routing through a transit hub is cheaper overall.
DC_TO_DC_CONNECTIONS: list[tuple[str, str]] = [
    ("DC01", "DC07"),   # Los Angeles ↔ Seattle   (I-5 Pacific corridor)
    ("DC01", "DC05"),   # Los Angeles ↔ Phoenix    (I-10 Southwest)
    ("DC01", "DC09"),   # Los Angeles ↔ Denver     (I-15 / I-70)
    ("DC02", "DC08"),   # Dallas ↔ Houston         (I-45, ~250 mi)
    ("DC02", "DC09"),   # Dallas ↔ Denver          (I-35 / I-25)
    ("DC02", "DC04"),   # Dallas ↔ Atlanta         (I-20 Deep South)
    ("DC03", "DC09"),   # Chicago ↔ Denver         (I-80 Midwest)
    ("DC03", "DC06"),   # Chicago ↔ New York       (I-80 / I-90 Northern)
    ("DC04", "DC10"),   # Atlanta ↔ Miami          (I-75 / I-95 Southeast)
    ("DC04", "DC06"),   # Atlanta ↔ New York       (I-85 / I-95 Eastern)
    ("DC06", "DC10"),   # New York ↔ Miami         (I-95 full East Coast)
    ("DC08", "DC10"),   # Houston ↔ Miami          (I-10 / I-75 Gulf Coast)
]


# ==============================================================================
# SECTION 2 -- SIMULATION CONSTANTS
# ==============================================================================

INVENTORY_THRESHOLD   = 50    # Units below this level -> shortage flag
INITIAL_INVENTORY_MIN = 30    # Lowest possible starting stock at a store
INITIAL_INVENTORY_MAX = 200   # Highest possible starting stock at a store
DC_STOCK_LEVEL        = 10_000  # DCs are modeled as having essentially unlimited stock
RESTOCK_AMOUNT        = 150   # Units delivered per restock shipment
DAILY_DEMAND_MIN      = 10    # Min units sold per store per day
DAILY_DEMAND_MAX      = 60    # Max units sold per store per day
SHORTAGE_START_PROB   = 0.25  # Probability a store initialises in shortage


# ==============================================================================
# SECTION 3 -- HAVERSINE FORMULA
#
#   Computes the great-circle ("as-the-crow-flies") distance between two
#   points on Earth given their latitude/longitude in decimal degrees.
#
#   We then multiply by a road-factor (1.3) to approximate driving distance,
#   because trucks follow highway networks, not straight lines.
#
#   Formula:
#     a  = sin²(Δφ/2) + cos(φ₁)·cos(φ₂)·sin²(Δλ/2)
#     c  = 2·atan2(√a, √(1−a))
#     d  = R·c          where R = Earth radius in miles
# ==============================================================================

def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Return the approximate driving distance (miles) between two coordinates.

    Args:
        lat1, lon1 : Decimal degrees for point A (e.g., DC location)
        lat2, lon2 : Decimal degrees for point B (e.g., store location)

    Returns:
        Estimated driving distance in miles (float, rounded to 2 dp)
    """
    R = 3_958.8          # Earth's mean radius in miles

    # Convert degrees -> radians
    phi1    = math.radians(lat1)
    phi2    = math.radians(lat2)
    d_phi   = math.radians(lat2 - lat1)
    d_lam   = math.radians(lon2 - lon1)

    # Core Haversine computation
    a = (math.sin(d_phi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    straight_line = R * c           # great-circle distance

    ROAD_FACTOR = 1.3               # highway detours add ~30 % to crow-flies distance
    return round(straight_line * ROAD_FACTOR, 2)


# ==============================================================================
# SECTION 4 -- LOGISTICS GRAPH
#
#   Adjacency-list representation of the supply chain network.
#
#   Nodes  -> Distribution Centers and Retail Stores
#   Edges  -> Routes between them, weighted by estimated driving miles
#
#   In real knowledge-graph systems used by conversational AI, nodes represent
#   entities (products, SKUs, facilities) and edges encode relationships
#   (ships-to, located-at, restocks-from) with numeric properties (distance,
#   cost, lead time).  Our graph is a simplified but structurally identical
#   version of that pattern.
# ==============================================================================

class LogisticsGraph:
    """
    Weighted, undirected graph for the US supply chain network.

    Attributes:
        adjacency : {node_id: [(neighbor_id, weight), ...]}
        nodes     : {node_id: metadata_dict}
    """

    def __init__(self):
        # defaultdict avoids KeyError on first access for any node
        self.adjacency: dict[str, list[tuple[str, float]]] = defaultdict(list)
        self.nodes: dict[str, dict] = {}

    def add_node(self, node_id: str, metadata: dict) -> None:
        """Register a node (DC or store) with its geographic/type metadata."""
        self.nodes[node_id] = metadata

    def add_edge(self, u: str, v: str, weight: float) -> None:
        """
        Add an undirected edge between u and v with the given weight (miles).
        Both directions are stored because trucks can travel either way.
        """
        self.adjacency[u].append((v, weight))
        self.adjacency[v].append((u, weight))

    def get_neighbors(self, node_id: str) -> list[tuple[str, float]]:
        """Return all (neighbor_id, distance) pairs reachable from node_id."""
        return self.adjacency.get(node_id, [])

    def node_count(self) -> int:
        """Total number of nodes in the graph."""
        return len(self.nodes)

    def edge_count(self) -> int:
        """
        Total number of undirected edges.
        Each undirected edge is stored in both directions, so we halve the sum.
        """
        return sum(len(nbrs) for nbrs in self.adjacency.values()) // 2


# ==============================================================================
# SECTION 5 -- DIJKSTRA'S ALGORITHM (FROM SCRATCH)
#
#   Finds the single-source shortest paths from `source` to every other node
#   in a non-negatively-weighted graph.
#
#   Time complexity : O((V + E) log V)   using a binary min-heap
#   Space complexity: O(V)               for distances + predecessors
#
#   Why Dijkstra for supply chains?
#   --------------------------------
#   Each "edge weight" represents real cost (miles driven, fuel burned, time).
#   Dijkstra guarantees finding the globally cheapest route to each node,
#   which directly maps to the business objective of minimising shipping cost.
#   At Amazon scale, variants of Dijkstra (A*, bidirectional) are embedded
#   inside every package routing decision.
# ==============================================================================

def dijkstra(graph: LogisticsGraph, source: str) -> tuple[dict[str, float], dict[str, str | None]]:
    """
    Dijkstra's Single-Source Shortest Path algorithm.

    Algorithm steps
    ---------------
    1. Set dist[source] = 0, dist[all others] = ∞.
    2. Push (0, source) onto the min-heap.
    3. Pop the node u with the smallest known distance.
    4. Skip u if already finalised ("lazy deletion" pattern).
    5. For each edge (u -> v, w):
           if dist[u] + w < dist[v]:
               dist[v]    = dist[u] + w      <- relaxation
               prev[v]    = u
               push (dist[v], v) onto heap
    6. Repeat from step 3 until the heap is empty.

    Args:
        graph  : The LogisticsGraph to search
        source : Starting node ID (e.g., a store that needs restocking)

    Returns:
        distances    : {node_id -> shortest distance from source}
        predecessors : {node_id -> previous node on the shortest path}
    """
    INF = float('inf')

    # Initialise every node's tentative distance as infinity
    distances: dict[str, float] = {node: INF for node in graph.nodes}
    distances[source] = 0.0

    # predecessors[v] = the node visited just before v on the optimal path
    predecessors: dict[str, str | None] = {node: None for node in graph.nodes}

    # Set of nodes whose shortest path has been permanently decided
    finalised: set[str] = set()

    # Min-heap: entries are (tentative_distance, node_id)
    # heapq.heappop always returns the entry with the smallest distance
    heap: list[tuple[float, str]] = [(0.0, source)]

    while heap:
        # -- Step 3: extract the cheapest unvisited node ----------------------
        current_dist, current_node = heapq.heappop(heap)

        # -- Step 4: lazy deletion -- skip stale heap entries -----------------
        # A node may be in the heap multiple times with different distances.
        # Once finalised, any later pop for the same node is outdated.
        if current_node in finalised:
            continue
        finalised.add(current_node)

        # -- Step 5: edge relaxation ------------------------------------------
        for neighbor, edge_weight in graph.get_neighbors(current_node):
            if neighbor in finalised:
                continue   # already settled, cannot improve further

            candidate = current_dist + edge_weight

            if candidate < distances[neighbor]:
                # We found a cheaper path to 'neighbor' -- update and re-queue
                distances[neighbor]    = candidate
                predecessors[neighbor] = current_node
                heapq.heappush(heap, (candidate, neighbor))

    return distances, predecessors


def reconstruct_path(predecessors: dict[str, str | None], source: str, target: str) -> list[str]:
    """
    Trace the predecessors dictionary backward from `target` to `source`
    to rebuild the full optimal route as an ordered list of node IDs.

    Args:
        predecessors : Output from dijkstra()
        source       : Origin node ID
        target       : Destination node ID

    Returns:
        Ordered list of node IDs [source, ..., target], or [] if unreachable.
    """
    path: list[str] = []
    current: str | None = target

    # Walk backward through the predecessor chain
    while current is not None:
        path.append(current)
        current = predecessors.get(current)

    path.reverse()   # reverse so path runs source -> target

    # Sanity check: if we couldn't reach source, return empty
    if not path or path[0] != source:
        return []

    return path


# ==============================================================================
# SECTION 6 -- SUPPLY CHAIN OPTIMIZER (CORE ENGINE)
#
#   Ties the graph, Dijkstra, inventory, and simulation together.
#
#   In production e-commerce systems this class maps to a "fulfillment engine"
#   that interfaces with:
#     * Real-time inventory databases (DynamoDB, Spanner)
#     * Order management systems (OMS)
#     * Transportation management systems (TMS) for carrier selection
#     * Demand-forecasting ML models (Prophet, XGBoost)
#
#   Our version models the same logical flow using in-memory state.
# ==============================================================================

class SupplyChainOptimizer:
    """
    Core simulation engine for the US supply chain network.

    Public interface
    ----------------
    get_inventory_summary()          -> print current stock levels
    find_optimal_dc_for_store(sid)   -> (dc_id, path, distance)
    restock_store(sid)               -> execute one restocking transaction
    run_daily_restocking()           -> restock all shortage stores for one day
    simulate_daily_demand()          -> apply random customer demand
    run_week_simulation()            -> run 7 days end-to-end
    show_sample_paths()              -> print Dijkstra demo outputs
    """

    def __init__(self, seed: int = 42):
        random.seed(seed)
        self.graph      = LogisticsGraph()
        self.inventory: dict[str, int]  = {}    # store_id -> units on hand
        self.dc_stock:  dict[str, int]  = {}    # dc_id    -> units on hand
        self.transactions: list[dict]   = []    # full audit trail of shipments
        self.current_day: int           = 1

        # Populated by restock_store(); used for map visualisation
        # {store_id: (supplying_dc_id, route_path, total_miles)}
        self.restock_routes: dict[str, tuple[str, list[str], float]] = {}

        self._build_graph()
        self._initialize_inventory()

    # -- Graph Construction -----------------------------------------------------

    def _build_graph(self) -> None:
        """
        Build the full logistics network graph:

          Phase 1: Register all DC and Store nodes.
          Phase 2: DC ↔ Store full bipartite connections.
                   Every DC can supply every store; weight = Haversine miles.
          Phase 3: DC ↔ DC interstate corridor connections.
                   Enables multi-hop routing through transit hubs.

        The full bipartite DC-Store mesh is the standard "hub-and-spoke"
        topology used by retail giants.  A store in, say, Raleigh NC can
        be cheaply served by the Atlanta DC (closest hub) without needing
        a direct connection to every other DC in the graph.
        """

        # -- Phase 1: nodes ----------------------------------------------------
        for dc in DISTRIBUTION_CENTERS:
            self.graph.add_node(dc["id"], {**dc, "node_type": "DC"})
            self.dc_stock[dc["id"]] = DC_STOCK_LEVEL

        for store in RETAIL_STORES:
            self.graph.add_node(store["id"], {**store, "node_type": "store"})

        # -- Phase 2: DC ↔ Store edges (bipartite mesh) ------------------------
        for dc in DISTRIBUTION_CENTERS:
            for store in RETAIL_STORES:
                dist = haversine_miles(dc["lat"], dc["lon"],
                                       store["lat"], store["lon"])
                self.graph.add_edge(dc["id"], store["id"], dist)

        # -- Phase 3: DC ↔ DC interstate corridors ----------------------------
        for dc_a_id, dc_b_id in DC_TO_DC_CONNECTIONS:
            dc_a = next(d for d in DISTRIBUTION_CENTERS if d["id"] == dc_a_id)
            dc_b = next(d for d in DISTRIBUTION_CENTERS if d["id"] == dc_b_id)
            dist = haversine_miles(dc_a["lat"], dc_a["lon"],
                                   dc_b["lat"], dc_b["lon"])
            self.graph.add_edge(dc_a_id, dc_b_id, dist)

        print(f"  [Graph] Network ready: "
              f"{self.graph.node_count()} nodes, "
              f"{self.graph.edge_count()} edges")

    # -- Inventory Initialisation -----------------------------------------------

    def _initialize_inventory(self) -> None:
        """
        Assign random starting inventory to each retail store.
        SHORTAGE_START_PROB of stores intentionally start below the threshold
        to model pre-existing supply gaps -- a realistic scenario after a
        high-demand period (holidays, flash sales).
        """
        for store in RETAIL_STORES:
            if random.random() < SHORTAGE_START_PROB:
                # Store starts with a shortage (below threshold)
                qty = random.randint(INITIAL_INVENTORY_MIN, INVENTORY_THRESHOLD - 1)
            else:
                # Store starts with adequate stock
                qty = random.randint(INVENTORY_THRESHOLD, INITIAL_INVENTORY_MAX)
            self.inventory[store["id"]] = qty

    # -- Inventory Queries ------------------------------------------------------

    def get_shortage_stores(self) -> list[str]:
        """Return IDs of all stores currently below INVENTORY_THRESHOLD."""
        return [sid for sid, qty in self.inventory.items()
                if qty < INVENTORY_THRESHOLD]

    def get_inventory_summary(self) -> None:
        """Print a formatted stock-level report for every retail store."""
        print("\n" + "=" * 70)
        print(f"  INVENTORY STATUS REPORT  --  Day {self.current_day}")
        print("=" * 70)
        print(f"  {'ID':5s}  {'City':<20s} {'ST':3s}  {'Units':>6s}  {'Bar':<35s}  Status")
        print("-" * 70)

        shortage_count = 0
        for store in RETAIL_STORES:
            sid    = store["id"]
            qty    = self.inventory[sid]
            is_low = qty < INVENTORY_THRESHOLD
            if is_low:
                shortage_count += 1
            bar_len = min(qty // 5, 35)
            bar     = "#" * bar_len
            status  = "!!! SHORTAGE !!!" if is_low else "OK"
            print(f"  {sid:5s}  {store['city']:<20s} {store['state']:3s}  {qty:6d}  "
                  f"{bar:<35s}  {status}")

        print("-" * 70)
        print(f"  Shortage count: {shortage_count} / {len(RETAIL_STORES)} stores")
        print("=" * 70 + "\n")

    # -- Dijkstra-Based Optimal Restocking --------------------------------------

    def find_optimal_dc_for_store(self, store_id: str) -> tuple[str | None, list[str], float]:
        """
        Apply Dijkstra from the given store to find the nearest DC.

        We run Dijkstra with the *store* as the source node.  Because the
        graph is undirected and edge weights are symmetric, this gives us
        the shortest distance from every DC to the store in one pass --
        O((V+E) log V) for the entire network.

        Among all DCs, we select the one with the minimum path cost (miles).

        In production, we would also factor in:
          - DC stock availability (skip DCs with insufficient inventory)
          - Carrier service levels (overnight vs. ground)
          - Current traffic / road-closure weights
          - Carrier cost-per-mile by truck class

        Args:
            store_id : ID of the shortage store

        Returns:
            (best_dc_id, path_list, total_miles)
            Returns (None, [], inf) if no DC is reachable.
        """
        distances, predecessors = dijkstra(self.graph, store_id)

        best_dc:   str | None = None
        best_dist: float      = float('inf')

        for dc in DISTRIBUTION_CENTERS:
            dc_id = dc["id"]
            if distances[dc_id] < best_dist:
                best_dist = distances[dc_id]
                best_dc   = dc_id

        if best_dc is None:
            return (None, [], float('inf'))

        # Reconstruct the route: store -> ... -> best_dc
        path = reconstruct_path(predecessors, store_id, best_dc)
        return (best_dc, path, best_dist)

    def restock_store(self, store_id: str) -> dict | None:
        """
        Execute a single restocking shipment for a store in shortage.

        Transaction steps
        -----------------
        1. Confirm shortage still exists (demand may have fluctuated).
        2. Run Dijkstra to identify cheapest supplying DC.
        3. Deduct RESTOCK_AMOUNT units from DC stock.
        4. Add  RESTOCK_AMOUNT units to store inventory.
        5. Append a full transaction record for auditing / reporting.

        Returns:
            Transaction dict on success, or None if no shortage exists.
        """
        if self.inventory[store_id] >= INVENTORY_THRESHOLD:
            return None   # store was already adequately stocked

        dc_id, path, dist = self.find_optimal_dc_for_store(store_id)

        if dc_id is None:
            print(f"  [ERROR] No reachable DC for store {store_id}!")
            return None

        before_qty = self.inventory[store_id]
        self.inventory[store_id] += RESTOCK_AMOUNT
        self.dc_stock[dc_id]     -= RESTOCK_AMOUNT

        store_meta = self.graph.nodes[store_id]
        dc_meta    = self.graph.nodes[dc_id]

        txn = {
            "day":              self.current_day,
            "store_id":         store_id,
            "store_name":       store_meta["name"],
            "store_city":       store_meta["city"],
            "dc_id":            dc_id,
            "dc_name":          dc_meta["name"],
            "dc_city":          dc_meta["city"],
            "path":             path,
            "distance_mi":      dist,
            "qty_shipped":      RESTOCK_AMOUNT,
            "inventory_before": before_qty,
            "inventory_after":  self.inventory[store_id],
        }
        self.transactions.append(txn)
        # Cache route for map visualisation
        self.restock_routes[store_id] = (dc_id, path, dist)
        return txn

    # -- Daily Operations -------------------------------------------------------

    def simulate_daily_demand(self) -> None:
        """
        Deduct random consumer demand from every retail store's inventory.

        Each store sells between DAILY_DEMAND_MIN and DAILY_DEMAND_MAX units.
        Stock cannot fall below zero (represents a complete sell-out; no
        negative inventory in the physical world).

        Real-world context:
            Demand at actual retailers is modelled by time-series ML models
            (Facebook Prophet, LSTM neural networks) trained on historical
            POS data, seasonality, promotions, and weather.  Proactive
            replenishment -- ordering *before* you run out -- is the goal.
            Our uniform random model is intentionally simplified for clarity.
        """
        for store in RETAIL_STORES:
            sid    = store["id"]
            demand = random.randint(DAILY_DEMAND_MIN, DAILY_DEMAND_MAX)
            self.inventory[sid] = max(0, self.inventory[sid] - demand)

    def run_daily_restocking(self) -> None:
        """
        Detect all shortage stores and dispatch optimal restock shipments.
        This is the core daily optimization loop.
        """
        shortages = self.get_shortage_stores()

        if not shortages:
            print(f"  Day {self.current_day}: All {len(RETAIL_STORES)} stores "
                  f"are adequately stocked.  No restocking needed.")
            return

        print(f"  Day {self.current_day}: {len(shortages)} shortage(s) detected -- "
              f"optimising routes via Dijkstra...")

        for store_id in shortages:
            txn = self.restock_store(store_id)
            if txn:
                # Build a human-readable route string (city names only)
                route_cities = " -> ".join(
                    self.graph.nodes[n]["city"] for n in txn["path"]
                )
                print(f"    + {txn['store_city']:<18s} <- {txn['dc_city']:<15s} "
                      f"({txn['distance_mi']:>7.1f} mi)  "
                      f"Stock: {txn['inventory_before']} -> {txn['inventory_after']}")

    # -- Week Simulation --------------------------------------------------------

    def run_week_simulation(self) -> None:
        """
        Simulate a full 7-day distribution week.

        Each simulated day:
          Morning  -- customers purchase goods; demand reduces store inventory.
          Midday   -- inventory management system detects shortages.
          Evening  -- Dijkstra finds optimal DC for each shortage; shipments sent.
          Midnight -- inventory levels updated with received goods.

        This mirrors the actual "replenishment cycle" in retail logistics:
        stores submit end-of-day inventory snapshots, the distribution
        management system (DMS) processes overnight orders, and trucks
        depart at 04:00 for same-day or next-morning delivery.

        After the simulation, a summary report is printed covering total
        shipments, miles driven, and units distributed.
        """
        start_day = self.current_day

        print("\n" + "=" * 70)
        print(f"  WEEKLY SIMULATION  (days {start_day} - {start_day + 6})")
        print("=" * 70)

        txn_count_before = len(self.transactions)

        for offset in range(7):
            self.current_day = start_day + offset
            print(f"\n  {'-'*65}")
            print(f"  DAY {self.current_day}")
            print(f"  {'-'*65}")
            self.simulate_daily_demand()
            self.run_daily_restocking()

        self.current_day = start_day + 7   # advance clock past the week

        # -- Weekly summary ----------------------------------------------------
        week_txns  = self.transactions[txn_count_before:]
        total_mi   = sum(t["distance_mi"] for t in week_txns)
        total_units= sum(t["qty_shipped"]  for t in week_txns)

        print("\n" + "=" * 70)
        print("  WEEKLY SUMMARY")
        print("-" * 70)
        print(f"  Restocking shipments : {len(week_txns)}")
        print(f"  Total miles driven   : {total_mi:>10,.1f} mi")
        print(f"  Total units shipped  : {total_units:>10,} units")
        if week_txns:
            avg_dist = total_mi / len(week_txns)
            print(f"  Avg distance / trip  : {avg_dist:>10,.1f} mi")
        print("=" * 70 + "\n")

    # -- Educational Path Demo --------------------------------------------------

    def show_sample_paths(self) -> None:
        """
        Print five concrete Dijkstra examples covering different US regions.

        For each pair (DC -> Store):
          * Run Dijkstra from the DC
          * Show the shortest path as a sequence of city names
          * Show total distance and current store inventory status

        This helps illustrate how the algorithm naturally picks regional
        hubs: NYC -> Boston is far shorter than LA -> Boston, so
        the algorithm never chooses the cross-country route.
        """
        print("\n" + "=" * 70)
        print("  SAMPLE SHORTEST PATH CALCULATIONS  (Dijkstra Demo)")
        print("=" * 70)

        examples = [
            ("DC06", "ST30"),   # New York  -> Boston
            ("DC01", "ST02"),   # LA        -> San Francisco
            ("DC04", "ST23"),   # Atlanta   -> Birmingham
            ("DC03", "ST09"),   # Chicago   -> Minneapolis
            ("DC09", "ST05"),   # Denver    -> Salt Lake City
        ]

        for dc_id, store_id in examples:
            dc_meta    = self.graph.nodes[dc_id]
            store_meta = self.graph.nodes[store_id]
            inv        = self.inventory.get(store_id, 0)
            status     = "SHORTAGE" if inv < INVENTORY_THRESHOLD else "OK"

            # Run Dijkstra once from this DC
            distances, predecessors = dijkstra(self.graph, dc_id)
            dist = distances[store_id]
            path = reconstruct_path(predecessors, dc_id, store_id)
            route_str = " -> ".join(self.graph.nodes[n]["city"] for n in path)

            print(f"\n  {dc_meta['city']:<16s}  ->  {store_meta['city']}")
            print(f"    Distance  : {dist:,.1f} miles")
            print(f"    Route     : {route_str}")
            print(f"    Inventory : {inv} units  [{status}]")

        print("\n" + "=" * 70 + "\n")


# ==============================================================================
# SECTION 7 -- FOLIUM MAP VISUALISATION
#
#   Renders an interactive Leaflet.js map (via Folium) that shows the
#   full supply chain network in a browser-friendly HTML file.
#
#   Map encoding:
#     Blue star markers  = Distribution Centers
#     Green circles      = Stores with adequate stock
#     Red circles        = Stores with inventory shortages
#     Orange dashed lines= Active restock routes (DC -> Store)
# ==============================================================================

def generate_map(optimizer: SupplyChainOptimizer,
                 output_path: str = "supply_chain_map.html") -> None:
    """
    Build and save an interactive Folium map of the supply chain.

    Each marker has a clickable popup showing city, stock level, and
    status.  Restock routes drawn as dashed lines help visualise
    Dijkstra's routing decisions spatially.

    Args:
        optimizer   : Populated SupplyChainOptimizer instance
        output_path : Filename for the output HTML file
    """
    if not FOLIUM_AVAILABLE:
        print("\n  [ERROR] folium is not installed -- cannot generate map.")
        print("          Run:  pip install folium\n")
        return

    # -- Base map --------------------------------------------------------------
    # Centre over the continental US; CartoDB Positron is a clean grey basemap
    usa_centre = [39.5, -98.35]
    m = folium.Map(location=usa_centre, zoom_start=4, tiles="CartoDB positron")

    # -- Distribution Center markers (blue) ------------------------------------
    for dc in DISTRIBUTION_CENTERS:
        dc_id   = dc["id"]
        stock   = optimizer.dc_stock[dc_id]
        popup_html = (f"<b>{dc['name']}</b><br>"
                      f"City : {dc['city']}, {dc['state']}<br>"
                      f"Stock: {stock:,} units")

        folium.Marker(
            location=[dc["lat"], dc["lon"]],
            popup=folium.Popup(popup_html, max_width=260),
            tooltip=f"DC: {dc['city']}",
            icon=folium.Icon(color="blue", icon="industry", prefix="fa")
        ).add_to(m)

    # -- Retail Store markers (green = OK, red = shortage) ---------------------
    shortage_ids = set(optimizer.get_shortage_stores())

    for store in RETAIL_STORES:
        sid       = store["id"]
        inv       = optimizer.inventory[sid]
        is_short  = sid in shortage_ids
        colour    = "red" if is_short else "green"
        status_lbl= f"SHORTAGE ({inv} units)" if is_short else f"OK ({inv} units)"

        popup_html = (f"<b>{store['name']}</b><br>"
                      f"City : {store['city']}, {store['state']}<br>"
                      f"Inv  : {inv} units<br>"
                      f"Status: <b style='color:{colour}'>{status_lbl}</b>")

        folium.CircleMarker(
            location=[store["lat"], store["lon"]],
            radius=9,
            color=colour,
            fill=True,
            fill_color=colour,
            fill_opacity=0.75,
            popup=folium.Popup(popup_html, max_width=260),
            tooltip=f"{store['city']}: {inv} units",
        ).add_to(m)

    # -- Restock route lines (orange dashed) -----------------------------------
    # These lines represent the Dijkstra-optimal paths found during simulation.
    for store_id, (dc_id, path, dist) in optimizer.restock_routes.items():
        s_meta = optimizer.graph.nodes[store_id]
        d_meta = optimizer.graph.nodes[dc_id]

        folium.PolyLine(
            locations=[
                [d_meta["lat"], d_meta["lon"]],    # DC end
                [s_meta["lat"], s_meta["lon"]],    # Store end
            ],
            color="orange",
            weight=2.5,
            opacity=0.75,
            dash_array="10 5",
            tooltip=f"{d_meta['city']} -> {s_meta['city']}  ({dist:,.0f} mi)",
        ).add_to(m)

    # -- HTML legend (fixed bottom-left) ---------------------------------------
    legend_html = """
    <div style="
        position: fixed; bottom: 35px; left: 35px; z-index: 9999;
        background: white; padding: 14px 18px;
        border: 2px solid #888; border-radius: 8px;
        font-family: Arial, sans-serif; font-size: 13px; line-height: 1.7;
        box-shadow: 3px 3px 8px rgba(0,0,0,0.2);">
      <b>Supply Chain Map</b><br>
      <span style="color:blue;  font-size:18px;">&#9733;</span> Distribution Center<br>
      <span style="color:green; font-size:16px;">&#9679;</span> Store -- Adequate Stock<br>
      <span style="color:red;   font-size:16px;">&#9679;</span> Store -- Shortage<br>
      <span style="color:orange;">&#9135;&#9135;&#9135;</span> Active Restock Route (Dijkstra)
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # -- Save and open ---------------------------------------------------------
    m.save(output_path)
    abs_path = os.path.abspath(output_path)
    print(f"\n  [Map] Saved to: {abs_path}")
    print("  Open this file in any web browser to view the interactive map.\n")

    try:
        import webbrowser
        webbrowser.open(f"file:///{abs_path}")
        print("  [Map] Attempting to open in your default browser...")
    except Exception:
        pass   # If auto-open fails, the file is still saved and usable


# ==============================================================================
# SECTION 8 -- COMMAND-LINE MENU
# ==============================================================================

def print_banner() -> None:
    """Display the application title and network summary."""
    print("""
+==============================================================+
|        SUPPLY CHAIN OPTIMIZER  --  CSCI 355 Demo             |
|  Dijkstra's Algorithm  x  Haversine Distance  x  Folium     |
+==============================================================+

  Network  : 10 Distribution Centers + 30 Retail Stores (US)
  Algorithm: Dijkstra shortest path (heapq, built from scratch)
  Distance : Haversine formula x 1.3 road-factor (miles)
  Viz      : Folium interactive HTML map
""")


def menu_loop(optimizer: SupplyChainOptimizer) -> None:
    """
    Interactive CLI loop.  Runs until the user chooses to exit.
    All state (inventory, transactions, day counter) persists between
    menu calls within the same session.
    """
    options = {
        "1": ("View current inventory status",    lambda: optimizer.get_inventory_summary()),
        "2": ("Run one-week simulation (7 days)", lambda: optimizer.run_week_simulation()),
        "3": ("Generate & open interactive map",  lambda: generate_map(optimizer)),
        "4": ("Show sample shortest paths",       lambda: optimizer.show_sample_paths()),
        "5": ("Reset simulation (new random seed)",
              lambda: _reset(optimizer)),
        "6": ("Exit", None),
    }

    while True:
        print("\n+---------------------------------------+")
        print("|           MAIN MENU                   |")
        print("+---------------------------------------+")
        for key, (label, _) in options.items():
            print(f"|  {key}. {label:<35s}|")
        print("+---------------------------------------+")

        choice = input("  Enter choice [1-6]: ").strip()

        if choice not in options:
            print("  [!] Invalid choice -- please enter 1 through 6.")
            continue

        label, action = options[choice]

        if choice == "6":
            print("\n  Goodbye!  Supply chain optimised.\n")
            break

        action()


def _reset(optimizer: SupplyChainOptimizer) -> None:
    """Reinitialise the optimizer in-place with a fresh random seed."""
    new_seed = random.randint(0, 99_999)
    print(f"\n  Resetting simulation with seed = {new_seed} ...")
    optimizer.__init__(seed=new_seed)
    print(f"  Done.  Day counter reset to 1.")


# ==============================================================================
# SECTION 9 -- ENTRY POINT
# ==============================================================================

def main() -> None:
    """Initialise the supply chain and launch the interactive menu."""
    print_banner()

    print("  Building logistics network and initialising inventory...")
    optimizer = SupplyChainOptimizer(seed=42)
    print(f"  Ready.  {len(DISTRIBUTION_CENTERS)} DCs, "
          f"{len(RETAIL_STORES)} stores, "
          f"{optimizer.graph.edge_count()} routes loaded.\n")

    menu_loop(optimizer)


if __name__ == "__main__":
    main()
