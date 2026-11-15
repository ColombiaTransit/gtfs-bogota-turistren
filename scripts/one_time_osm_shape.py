#!/usr/bin/env python3
"""One-off OSM rail shape candidate; review visually before committing to data/."""
import heapq
import json
import math
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# Roughly Bogotá Gran Estación via Usaquén to Zipaquirá (verify station coords separately).
ANCHORS = [(4.648994605275174,-74.10198771838998), (4.69063,-74.03803), (5.02164,-74.00115)]
QUERY = '[out:json][timeout:180];way["railway"~"^(rail|narrow_gauge)$"](4.63,-74.13,5.06,-73.96);(._;>;);out body;'
ENDPOINT = "https://overpass.kumi.systems/api/interpreter"
def distance(a, b):
    lat1, lon1 = a
    lat2, lon2 = b
    lat = math.radians((lat1+lat2)/2)
    return 111195 * math.hypot(lat1-lat2, (lon1-lon2)*math.cos(lat))
def shortest(graph, source, target):
    heap = [(0.0, source)]; costs = {source:0.0}; previous = {}
    while heap:
        cost, at = heapq.heappop(heap)
        if cost != costs[at]: continue
        if at == target:
            path = [at]
            while at in previous:
                at = previous[at];path.append(at)
            return list(reversed(path)), cost
        for nxt, length in graph.get(at, []):
            new = cost + length
            if new < costs.get(nxt, float("inf")):
                costs[nxt] = new; previous[nxt] = at;heapq.heappush(heap,(new,nxt))
    raise RuntimeError("OSM railway is disconnected between the required station anchors")
def main():
    req = Request(ENDPOINT + "?" + urlencode({"data":QUERY}),
                  headers={"User-Agent": "ColombiaTransit-Turistren-OSM-research/1.0"})
    with urlopen(req, timeout=240) as response:
        elements = json.load(response)["elements"]
    nodes = {e["id"]: (e["lat"], e["lon"]) for e in elements if e["type"]=="node"}
    graph = {}
    for way in elements:
        if way["type"] != "way": continue
        chain = way.get("nodes", [])
        for a,b in zip(chain, chain[1:]):
            if a not in nodes or b not in nodes: continue
            dist = distance(nodes[a], nodes[b])
            graph.setdefault(a,[]).append((b,dist))
            graph.setdefault(b,[]).append((a,dist))
    if not graph: raise RuntimeError("No railway network received")
    anchors = []
    for latlon in ANCHORS:
        node = min(graph, key=lambda n:distance(nodes[n],latlon))
        d = distance(nodes[node],latlon)
        if d>500: raise RuntimeError(f"Station too far from rail: {latlon}, {d:.1f} m")
        anchors.append(node)
        print(f"anchor {latlon}: OSM node {node} distance {d:.1f} m")
    left, d1 = shortest(graph,anchors[0], anchors[1])
    right, d2 = shortest(graph,anchors[1], anchors[2])
    track = left + right[1:]
    coords = [[nodes[n][1],nodes[n][0]] for n in track]
    length_km = (d1+d2)/1000
    print(f"{len(coords)} rail nodes, {length_km:.1f} km. MANUAL REVIEW REQUIRED")
    if not 25 < length_km < 100:
        raise RuntimeError("Implausible rail length; needs manual research")
    output = Path("candidate-rail-shape.geojson")
    output.write_text(json.dumps({"type":"Feature","properties":{
        "source":"OpenStreetMap contributors", "license":"ODbL", "reviewed":False,
        "route":"Gran Estación - Usaquén - Zipaquirá", "length_km":round(length_km,2)},
        "geometry":{"type":"LineString","coordinates":coords}},ensure_ascii=False))
    print(f"Wrote {output}, NOT ready for release; inspect shape and stop alignment")
if __name__=="__main__":
    main()
