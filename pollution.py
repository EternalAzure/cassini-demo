from datetime import datetime
from collections import namedtuple
from typing import TypeAlias, Literal, overload

import numpy as np
import pandas as pd

import geodata


Coordinate = namedtuple('Coordinate', ['lon', 'lat'])
Intake = namedtuple('Intake', ['cubics', 'litres'])

def find_nearest(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return array[idx]


def accumulation(dataset:pd.DataFrame, location:Coordinate, exposure_start:datetime, exposure_end:datetime, air_intake_cubics_per_minute:float=None, air_intake_litres_per_minute:float=None):
    if air_intake_cubics_per_minute and air_intake_litres_per_minute:
        raise ValueError("Give only either air_intake_cubics_per_minute or air_intake_litres_per_minute")
    if exposure_end < exposure_start:
        raise ValueError(f"Exposure can not end before it started. {exposure_start=} {exposure_end=}")
    if exposure_start == exposure_end: return 0

    # Find data at exposure location
    nearest_lon = find_nearest(dataset["lon"], location.lon)
    nearest_lat = find_nearest(dataset["lat"], location.lat)
    df = dataset[dataset["lon"] == nearest_lon]
    df = df[df["lat"] == nearest_lat]
    if len(df) == 0: raise ValueError("No data within exposure area")

    # Find data within exposure time
    start_time = exposure_start.hour
    end_time = exposure_end.hour
    if exposure_end.minute: end_time += 1
    df = df[df["leadtime"] >= start_time][df["leadtime"] < end_time]
    if exposure_end.hour > dataset["leadtime"].max(): raise ValueError("Exposure end time is too far into future")
    if len(df) == 0: raise ValueError("No data within exposure time")

    first_hour = df.iloc[:1]
    mid_hours = df.iloc[1:-1]
    last_hour = df.iloc[-1:]
    #last_hour:pd.Series = df.iloc[-1] if len(df) > 1 else df.iloc[0]

    # Set intake and multiplier
    if isinstance(air_intake_cubics_per_minute, int):
        in_take = air_intake_cubics_per_minute
        multiplier = 1
    elif isinstance(air_intake_litres_per_minute, int):
        in_take = air_intake_litres_per_minute
        multiplier = 0.001

    exposed_time = exposure_end - exposure_start
    hours_exposed = exposed_time.total_seconds() / 3600

    inhaled_pollutants_accumulation:float = 0
    if hours_exposed == 0: return 0
    if hours_exposed <= 1:
        if exposure_start.hour == exposure_end.hour:
            minutes_exposed = exposure_end.minute - exposure_start.minute
        else:
            minutes_exposed = 60 - exposure_start.minute + exposure_end.minute
        pollutants_in_unit_of_air:float = df.iloc[0]["value"] * multiplier # 1 or 0.001
        return pollutants_in_unit_of_air * minutes_exposed * in_take
    if hours_exposed < 2: mid_hours = df.iloc[0:0] # Empty
    
    # Calculate exposure amount
    for row in first_hour.iterrows():
        pollutants_in_unit_of_air:float = row[1]["value"] * multiplier # 1 or 0.001
        minutes_exposed = 60 - exposure_start.minute
        inhaled_pollutants_accumulation += pollutants_in_unit_of_air * minutes_exposed * in_take
    
    for row in mid_hours.iterrows():
        pollutants_in_unit_of_air:float = row[1]["value"] * multiplier # 1 or 0.001
        minutes_exposed = 60
        inhaled_pollutants_accumulation += pollutants_in_unit_of_air * minutes_exposed * in_take
    
    for row in last_hour.iterrows():
        pollutants_in_unit_of_air:float = row[1]["value"] * multiplier # 1 or 0.001
        minutes_exposed = 60 - exposure_end.minute
        inhaled_pollutants_accumulation += pollutants_in_unit_of_air * minutes_exposed * in_take

    return inhaled_pollutants_accumulation




if __name__ == "__main__":
    query = geodata.ForecastQuery(
        variable="PM10",
        time=datetime(2025, 5, 10, 0, 0),
        leadtimes=0,
        model=None,
        limits={"north": 60.5, "south": 60, "west": 20, "east": 20.5}
    )
    location = Coordinate(20.24, 60.26)
    data = geodata.get_dataframe(query)
    exposure_start = datetime(2025, 5, 10, 0, 0)
    exposure_end = datetime(2025, 5, 10, 1, )

    result2 = accumulation(data, location, exposure_start, exposure_end, air_intake_cubics_per_minute=1)
    print(f"{result2=}")