import json
from pathlib import Path

from geodata import GeoJSON, GeoJSONlimits


def crop_geojson(limits:GeoJSONlimits, geojson:GeoJSON|Path|str|None=None, target_filename:Path|str=None) -> GeoJSON:
    """Crop big geojson into smaller area. Defaults to europe.forecast.geo.json.
    If target path is given, writes a JSON-file. Only include a filename to the path."""
    if not isinstance(limits, dict): raise ValueError("limits should be a dict with keys: north, south, west, east")
    if ((not isinstance(limits, dict)) or
        ("north" not in limits.keys() or
        "south" not in limits.keys() or
        "west" not in limits.keys() or
        "east" not in limits.keys())): 
        raise ValueError("limits should be a dict with keys: north, south, west, east")
    if isinstance(target_filename, str) and ("/" in target_filename or "\\" in target_filename):
        raise ValueError("Target filename should only include filename")
    
    if geojson is None:
        with open("data/geojson/europe.forecast.geo.json", "r") as file:
            geojson = json.load(file)
    elif isinstance(geojson, (Path, str)):
        with open(geojson, "r") as file:
            geojson = json.load(file)
    elif isinstance(geojson, dict):
        if ("type" not in geojson.keys() or
            "features" not in geojson.keys()):
            raise ValueError("GeoJSON should have keys: 'type' and 'features'")
    
    sub_region = {
        "type": "FeatureCollection",
        "center": {"lat": round((limits["south"]+limits["north"])/2, 2), "lon": round((limits["west"]+limits["east"])/2, 2)},
        "limits": {
            "north": limits["north"],
            "south": limits["south"],
            "west": limits["west"],
            "east": limits["east"]
        },
        "features": []
    }

    for feature in geojson["features"]:
        centroid = feature["geometry"]["centroid"]
        lon = centroid[0]
        lat = centroid[1]
        location = {
            "type": "Feature",
            "id": feature["id"],
            "geometry": {
                "type": "Polygon",
                "centroid": centroid,
                "coordinates": feature["geometry"]["coordinates"]
            }
        }
        if (lon > limits["west"] and
            lon < limits["east"] and
            lat < limits["north"] and
            lat > limits["south"]):
            sub_region["features"].append(location)

    if target_filename:
        with open("data/geojson/target_filepath", "w") as file:
            file.write(json.dumps(sub_region))
    return sub_region

if __name__ == "__main__":
    result = crop_geojson({
        "north": 51,
        "south": 50,
        "west": 10,
        "east": 11
    })
    #print(result)