import itertools
import math

import pandas as pd

from bokeh.io import curdoc
from bokeh.models import (
    ColumnDataSource,
    Div,
    FactorRange,
    HoverTool,
    MultiChoice,
    Range1d,
    Span,
)
from bokeh.layouts import row, column
from bokeh.palettes import Spectral, Category20
from bokeh.plotting import figure
from s3fs.core import S3FileSystem

"""
Creates a `bokeh.documentation` for LinkedIn's Relative Skill Penetration
"""

def get_df(
    bucket="s3://wbgggscecovid19dev-datapartnership",
    key="data/linkedin/Skills/Country Level/TABLE 2. Relative Skill Penetration by Country.csv",
) -> pd.DataFrame:
    """
    Gets `pandas.DataFrame` from AWS S3
    """
    s3 = S3FileSystem()
    return pd.read_csv(s3.open(f"{bucket}/{key}", mode="rb"))

def get_data(df, countries, skills):
    """
    Creates a `bokeh.models.sources.ColumnDataSource`
    """
    x = list(itertools.product(skills, countries))

    # select subset for selected Skills and Countries
    df1 = pd.DataFrame(x, columns=["skill_group_name", "country_name"])
    df2 = df[pd.Series(zip(df["skill_group_name"], df["country_name"])).isin(x)]

    # complete cartesian product missing values
    y = pd.merge(df1, df2, on=["skill_group_name", "country_name"], how="outer")[
        "relative_skill_group_penetration"
    ].to_list()
    
    z = pd.merge(df1,df2, on= ["skill_group_name", "country_name"], how="outer")[
        "n_occupations_country_skill"
    ].to_list()
    
    data = dict(x=x, y=y, z=z)

    # Let 'bokeh.palettes` choose the color; otherwise, "blue"
    if 2 < len(countries) <= 11:
        data["color"] = len(skills) * Spectral[len(countries)]
    else:
        data["color"] = len(countries) * len(skills) * ["#1f77b4"]

    return data

select_skills = [
    "Artificial Intelligence (AI)",
    "Digital Literacy",
    "Human Computer Interaction",
    "Scientific Computing",
]
select_countries = [
    "Botswana",
    "Germany",
    "Kenya",
    "Mauritius",
    "Namibia",
    "Nigeria",
    "Poland",
    "South Africa",
]

# Plots
df = get_df()

all_skills = df["skill_group_name"].unique().tolist()
all_countries = df["country_name"].unique().tolist()

# Multichoice Options for Skills and Countries
skill_multi_choice = MultiChoice(
    value=select_skills,
    options=all_skills,
    title="Select Skills",
    delete_button=True,
    margin=30,
)

country_multi_choice = MultiChoice(
    value=select_countries,
    options=all_countries,
    title="Select Countries",
    delete_button=True,
    margin=30,
)

data = get_data(df, select_countries, select_skills)
source = ColumnDataSource(data)

p = figure(
    title="LinkedIn: Relative Skill Group Penetration",
    x_range=FactorRange(*data["x"]),
    sizing_mode="stretch_width",
)
p.min_border = 40
p.axis.axis_line_width = 2
p.x_range.range_padding = 0.05
# p.y_range = Range1d(0, 2.5)
p.xaxis.major_label_orientation = math.pi / 2
p.xgrid.grid_line_color = None

p.xaxis.axis_label = "Skill Group Name, Country"
p.yaxis.axis_label = "Relative Skill Group Penetration"

p.vbar(x="x", top="y", color="color", source=source, width=0.75)

hline = Span(
    location=1,
    dimension="width",
    line_dash="dashed",
    line_width=2,
    line_color="gray",
    line_alpha=0.5,
)

p.renderers.extend([hline])

p.line([], [], legend_label="Global Average", line_color="gray")

hover = HoverTool(
    tooltips=[
        ("Skill Group Name, Country", "@x"),
        ("Relative Skill Group Penetration", "@y"),
        ("No. of Occupations in this Country with Positive Skill Group Penetration for this Skill", "@z")
    ]
)
p.add_tools(hover)

def callback(attr, old, new):
    """
    Callback function to change `source` upon changes on Countries and Skills
    """
    select_countries = sorted(country_multi_choice.value)
    select_skills = sorted(skill_multi_choice.value)

    data = get_data(df, select_countries, select_skills)
    p.x_range.factors = data["x"]

    source.data = data

skill_multi_choice.on_change("value", callback)
country_multi_choice.on_change("value", callback)

# Layouts
widgets = column([skill_multi_choice, country_multi_choice], width=400)

div = Div(
    text="""
    <h1>LinkedIn: Relative Skill Group Penetration</h1>
    The metric captures the average penetration of a given skill group across all occupations in a country, as a ratio of the global average across the same occupation set. For example, the average penetration of Artificial Intelligence Skills across all occupations in India is 3.57X the global average across the same set of occupations.  
    Learn more on the <a href="https://docs.datapartnership.org/notebooks/linkedin/examples/linkedin_skills_benchmarking/linkedin_skills_benchmarking.html">documentation</a>.
    """,
)
footer = Div(
    text="""
    Data Source: <a href="https://datacatalog.worldbank.org/dataset/skills-linkedin-data">https://datacatalog.worldbank.org/dataset/skills-linkedin-data</a>.
    """,
)
layout = column(div, row(widgets, p), footer, sizing_mode="stretch_width")

curdoc().add_root(layout)

