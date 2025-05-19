import os
import json
import glob
import copy
import sqlite3
import pandas as pd
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TypeAlias, Literal, Optional

import numpy as np
import xarray as xr


GeoJSON: TypeAlias = dict[Literal["type", "center", "features", "limits"]]
GeoJSONlimits: TypeAlias = dict[Literal["north", "south", "west", "east"]]

@dataclass
class ForecastQuery:
    variable: Literal['PM2.5'
                    'PM2.5 Nitrate'
                    'PM2.5 Sulphate'
                    'PM2.5 REC'
                    'PM2.5 TEC'
                    'PM2.5 SIA'
                    'PM2.5 TOM'
                    'PM10'
                    'PM10 Dust'
                    'PM10 Salt'
                    'NH3'
                    'CO'
                    'HCHO'
                    'OCHCHO'
                    'NO2'
                    'VOCs'
                    'O3'
                    'NO + NO2'
                    'SO2'
                    'Alder pollen'
                    'Birch pollen'
                    'Grass pollen'
                    'Mugwort pollen'
                    'Olive pollen'
                    'Ragweed pollen']
    time: datetime
    leadtime: int|list[int] # 0 zero means at 00:00 o'clock tec.
    model: Optional[str]
    limits: Optional[GeoJSONlimits]

@dataclass
class ForecastMultiQuery:
    variable: Literal['PM2.5'
                    'PM2.5 Nitrate'
                    'PM2.5 Sulphate'
                    'PM2.5 REC'
                    'PM2.5 TEC'
                    'PM2.5 SIA'
                    'PM2.5 TOM'
                    'PM10'
                    'PM10 Dust'
                    'PM10 Salt'
                    'NH3'
                    'CO'
                    'HCHO'
                    'OCHCHO'
                    'NO2'
                    'VOCs'
                    'O3'
                    'NO + NO2'
                    'SO2'
                    'Alder pollen'
                    'Birch pollen'
                    'Grass pollen'
                    'Mugwort pollen'
                    'Olive pollen'
                    'Ragweed pollen']
    time: datetime
    leadtimes: list[int] # 0 zero means at 00:00 o'clock tec.
    model: Optional[str]
    limits: Optional[GeoJSONlimits]

@dataclass
class AnalysisQuery:
    variable: Literal['PM2.5'
                    'PM2.5 Nitrate'
                    'PM2.5 Sulphate'
                    'PM2.5 REC'
                    'PM2.5 TEC'
                    'PM2.5 SIA'
                    'PM2.5 TOM'
                    'PM10'
                    'PM10 Dust'
                    'PM10 Salt'
                    'NH3'
                    'CO'
                    'HCHO'
                    'OCHCHO'
                    'NO2'
                    'VOCs'
                    'O3'
                    'NO + NO2'
                    'SO2'
                    'Alder pollen'
                    'Birch pollen'
                    'Grass pollen'
                    'Mugwort pollen'
                    'Olive pollen'
                    'Ragweed pollen']
    start_time: datetime
    end_time: datetime



def query_forecast_db(query:ForecastQuery):
    leadtime = query.time + timedelta(hours=query.leadtimes)
    with sqlite3.connect("AirQuality.db") as conn:
        cursor = conn.cursor()
        parameters = {
            "variable": query.variable,
            "datetime": query.time.strftime("%Y/%m/%d %H:%M"), 
            "leadtime": leadtime.strftime("%Y/%m/%d %H:%M"), 
            "model": query.model
        }
        if not query.model:
            parameters.pop("model")
            sql = f"""
                SELECT variable_name, value, lon, lat, leadtime 
                FROM forecasts 
                WHERE variable_name=:variable AND datetime=:datetime AND leadtime<=:leadtime
            """
        else:
            sql = f"""
                SELECT variable_name, value, lon, lat, leadtime 
                FROM forecasts 
                WHERE variable_name=:variable AND datetime=:datetime AND leadtime<=:leadtime AND model=:model
            """
        results = cursor.execute(sql, parameters).fetchall()
        df = pd.DataFrame(results, columns=["variable", "value", "lon", "lat", "leadtime"])
        df['id'] = df.apply(lambda row: f"[{row['lon']}, {row['lat']}]", axis=1)
        df = df[['id'] + [col for col in df.columns if col != 'id']]
        return df


def query_forecast_nc(query:ForecastQuery):
    ds = xr.open_dataset("data/netcdf/cams-europe-air-quality-forecasts/EU-forecast-PM10-2025-05-10-24/ENS_FORECAST.nc", engine="netcdf4", decode_timedelta=False)
    all_values = ds.variables["pm10_conc"][query.leadtimes][0].data # lat lon
    all_longitudes = list(map(lambda lon: lon if lon < 180 else lon - 360, ds.variables["longitude"].data.tolist()))
    all_latitudes:list = ds.variables["latitude"].data.tolist()

    values = all_values
    longitude = all_longitudes
    latitude = all_latitudes
    if query.limits:
        # Find longitude index range
        west_limit_idx = min([i for i, lon in enumerate(all_longitudes) if lon > query.limits["west"]])
        east_limit_idx = max([i for i, lon in enumerate(all_longitudes) if lon < query.limits["east"]])

        # Find latitude index range (NOTE: descending order)
        north_limit_idx = min([i for i, lat in enumerate(all_latitudes) if lat < query.limits["north"]])
        south_limit_idx = max([i for i, lat in enumerate(all_latitudes) if lat > query.limits["south"]])

        # Crop the 1D coordinate arrays
        longitude = all_longitudes[west_limit_idx:east_limit_idx + 1]
        latitude = all_latitudes[north_limit_idx:south_limit_idx + 1]

        # Crop the 2D values array using lat (rows) and lon (columns)
        values = all_values[north_limit_idx:south_limit_idx + 1, west_limit_idx:east_limit_idx + 1]

    # Create coordinate matrix
    LON, LAT = np.meshgrid(longitude, latitude)
    matrix_np = np.stack((LON, LAT), axis=-1)
    coordinates = [[[round(lat[0],2), round(lat[1],2)] for lat in lon] for lon in matrix_np.tolist()] 

    values_expanded = values[:, :, np.newaxis] # Make it 3D so we can concatenate it

    # Add values to coordinates
    results = np.concatenate((values_expanded, coordinates), axis=2)

    # Add leadtime to coordinates
    time_array = np.full((len(latitude), len(longitude), 1), query.leadtimes)
    results = np.concatenate((results, time_array), axis=2)

    # Reshape results for pd.DataFrame
    flat_result = results.reshape(-1, 4) #2D

    df = pd.DataFrame(flat_result, columns=["value", "lon", "lat", "leadtime"])

    # Create id for plotly
    df['id'] = df.apply(lambda row: f"[{row['lon']}, {row['lat']}]", axis=1)

    # Move id-column to first
    df = df[['id'] + [col for col in df.columns if col != 'id']]
    return df


def query_analysis(query:AnalysisQuery):
    pass


def get_dataframe(query:ForecastMultiQuery|AnalysisQuery):
    if isinstance(query, ForecastMultiQuery):
        _query:ForecastQuery = copy.deepcopy(query)
        dfs = []
        for hour in query.leadtimes:
            _query.leadtimes = hour
            dfs.append(query_forecast_nc(_query))
        df = pd.concat(dfs, ignore_index=True)
        df = df.sort_values(by="leadtime", ascending=True)
        return df
    elif isinstance(query, AnalysisQuery):
        return query_analysis(query)
    raise ValueError(f"Query must be instance of either {ForecastMultiQuery.__name__} or {AnalysisQuery.__name__}")


def get_geojson(geojson_path:str):
    if os.path.exists(geojson_path):
        with open(geojson_path, "r") as file:
            geojson:GeoJSON = json.load(file) # Throws MemoryError
            return geojson

    print(f"No files found with {geojson_path=}")
    print(f"Here is a list of existing geojsons:")
    geojsons = glob.glob("data/geojson/*.geo.json")
    for file in geojsons:
        print(file)
    raise ValueError(f"No files found with {geojson_path=}")



if __name__ == "__main__":
    query = ForecastQuery(
        variable="PM10",
        time=datetime(2025, 5, 10, 0, 0),
        leadtime=4,
        model=None,
        limits={"north": 60, "south": 0, "west": -100, "east": 20}
    )

    df = get_dataframe(query)
    breakpoint()
    print("Miip!")