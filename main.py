import math

import dash
import pandas as pd
from dash import dcc, html, Input, Output, Patch, State
import plotly.graph_objects as go
from datetime import datetime, timedelta

import geodata
from geodata import ForecastMultiQuery, GeoJSON
import crop_geojson
from pollution import accumulation, Coordinate

# Region & data config
CITY_REGIONS = {
    "Paris": {"north": 54, "south": 44, "west": -4, "east": 8}
}

TIME_SPAN = 12
DATETIME = datetime(2025, 5, 10, 0, 0)

def get_geojson(region) -> GeoJSON:
    geojson_path = "data/geojson/europe.forecast.geo.json"
    return crop_geojson.crop_geojson(CITY_REGIONS[region], geojson_path)

def get_data(leadtime: int, geojson: GeoJSON):
    df = geodata.get_dataframe(ForecastMultiQuery(
        variable="PM10",
        time=DATETIME,
        leadtimes=[leadtime],
        model=None,
        limits=geojson["limits"]
    ))
    return df

def get_cumulative_exposure(time_span:int):
    df = geodata.get_dataframe(ForecastMultiQuery(
        variable="PM10",
        time=DATETIME,
        leadtimes=[_ for _ in range(time_span+1)],
        model=None,
        limits=geojson["limits"]
    ))
    cumulative_exposure = [accumulation(
        df, Coordinate(lon=2.35, lat=48.85), 
        DATETIME, DATETIME + timedelta(hours=i),
        air_intake_cubics_per_minute=1)
        for i in range(1, time_span+1)
    ]
    cumulative_exposure = [0] + cumulative_exposure
    return cumulative_exposure

# Initialize app and data
app = dash.Dash(__name__)
geojson = get_geojson("Paris")
locations = get_data(0, geojson).iloc[:, 0].tolist()
cumulative_exposure = get_cumulative_exposure(TIME_SPAN)


# Helper to build map figure
def create_map_figure(leadtime):
    df = get_data(leadtime, geojson)
    fig = go.Figure(go.Choroplethmap(
        geojson=geojson,
        featureidkey="id",
        locations=locations,
        z=df["value"],
        colorscale="Bupu",
        marker=dict(opacity=0.4, line_width=0),
        zmin=2,
        zmax=20
    ))
    fig.update_layout(
        map_center=dict(lon=2, lat=49),
        map_zoom=5,
        margin=dict(l=0, r=0, t=20, b=0),
    )
    return fig


def update_map_time(leadtime):
    fig = Patch()
    global geojson
    df = get_data(leadtime, geojson)
    fig.data[0].z = df["value"]
    return fig


# Helper to build scatter plot
def create_chart_figure(leadtime):
    fig = go.Figure(go.Scatter(
        x=[i for i in range(TIME_SPAN+1)],
        y=cumulative_exposure[:leadtime+1],
        mode="lines+markers",
        name="PM10"
    ),
    layout_yaxis_range=[-100, math.ceil(cumulative_exposure[-1]/100)*100], # NOTE setting y-axis allows to see climbing motion when slider in moved
    layout_xaxis_range=[-TIME_SPAN/10, TIME_SPAN+(TIME_SPAN/10)] # NOTE setting y-axis allows to see climbing motion when slider in moved
    )
    fig.update_layout(
        yaxis_title="PM10",
        xaxis_title="Leadtime",
        margin=dict(l=40, r=10, t=20, b=40)
    )
    return fig

# App layout
app.layout = html.Div([
    html.H3("Air Quality Forecast: Paris (PM10)"),
    
    html.Div([
        dcc.RadioItems(
            id="color",
            options=["Gradient", "Zones", "Viridis"],
            value="Gradient",
            inline=True
        ),
        dcc.Graph(id="map", figure=create_map_figure(0))
    ], style={"display": "inline-block", "width": "48%", "verticalAlign": "top"}),

    html.Div([
        dcc.Graph(id="chart", figure=create_chart_figure(0))
    ], style={"display": "inline-block", "width": "48%", "verticalAlign": "bottom"}),

    html.Div([
        dcc.Slider(
            id="leadtime-slider",
            min=0,
            max=12,
            step=1,
            value=0,
            marks={i: str(i) for i in range(TIME_SPAN+1)},
            tooltip={"always_visible": True}
        )
    ], style={"padding": "40px 10px 10px 10px"})
])

# Callback to update both plots
@app.callback(
    Output("map", "figure"),
    Output("chart", "figure"),
    Input("leadtime-slider", "value")
)
def update_figures(leadtime):
    return update_map_time(leadtime), create_chart_figure(leadtime)


@app.callback(
    Output("map", "figure", allow_duplicate=True),
    Input("color", "value"),
    prevent_initial_call=True
)
def change_color(color:str):
    print(f"Change color: {color}")
    zones = [(0,"#fcfafa"), (0.19,"#fcfafb"), (0.20,"#c7dff0"), (0.39,"#c7dff1"), (0.4,"#77baed"), (0.59,"#77baee"), (0.6,"#943fa2"), (0.79,"#943fa1"), (0.8,"#4d004a"), (1,"#4d004b")]
    bupu = [(0,"#f7fcfd"), (0.11,"#e0ecf4"), (0.33,"#bfd3e6"), (0.44,"#9ebcda"), (0.55,"#8c96c6"), (0.66,"#8c6bb1"), (0.77,"#88419d"), (0.88,"#810f7c"), (1,"#4d004b")]
    fig = Patch()
    fig.data[0].colorscale = color
    if color == "Gradient":
        fig.data[0].colorscale = bupu
    if color == "Zones":
        fig.data[0].colorscale = zones
    return fig




# Run app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050)
