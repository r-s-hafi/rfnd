from fastapi.responses import HTMLResponse
import pandas as pd
import random
import matplotlib.colors as mcolors
from sqlite3 import Connection
from datetime import datetime
import plotly.express as px
import plotly.io as pio
import re


class User:
    def __init__(self, session_token: str, current_plots: list):
        self.session_token = session_token
        self.current_plots = current_plots

class Tag:
    def __init__(self, id: str, data: pd.DataFrame | float, color: str):

        self.id = id
        self.data = data
        self.color = color

    #utility fxn, not using it to create an instance, so use @staticmethod
    @staticmethod
    def get_color() -> str:
            return random.choice(list(mcolors.CSS4_COLORS.keys()))

    @staticmethod
    def plot(self, con_data: Connection, start_time: datetime, end_time: datetime) -> str:
        
        #validate tag.id to prevent SQL injection
        #only allow alphanumeric characters, underscores, and spaces (SQLite identifiers)
        if not re.match(r'^[a-zA-Z0-9_ ]+$', self.id):
            return HTMLResponse(f"Invalid tag ID format: {self.id}. Only alphanumeric characters, underscores, and spaces are allowed.")
        
        #read the data from the database
        df = pd.read_sql(f"""SELECT Time, "{self.id}"
                            FROM process_data
                            WHERE Time >= ? AND Time <= ? AND "{self.id}" IS NOT NULL""", con_data, params=(start_time, end_time))

        #convert the tag_id column to numeric to ensure proper formatting
        df[self.id] = pd.to_numeric(df[self.id], errors='coerce')
        fig = px.line(df, x="Time", y=self.id, title=f"{self.id}", labels={'Time': 'Time', self.id: 'Value'}, color_discrete_sequence=[self.color])
            
        #configure the plot to be dark mode with better contrast
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor='#1c2128',
            plot_bgcolor='#0d1117',
            font=dict(color='#c9d1d9', size=12),
            title_font=dict(size=16, color='#e6edf3'),
            xaxis=dict(
                gridcolor='#30363d',
                showgrid=False,
                zeroline=False,
                tickformat= '%m/%d/%Y %H:%M'
            ),
            yaxis=dict(
                gridcolor='#30363d',
                showgrid=False,
                zeroline=False,
                tickformat='.3g',
            ),
            margin=dict(l=60, r=40, t=60, b=50),
            hovermode='x unified'
        )
        #format hover tooltips to show 3 significant figures
        fig.update_traces(hovertemplate='%{x}<br>%{y:.3g}<extra></extra>')

        return pio.to_html(fig, config={'responsive': True})
