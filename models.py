from fastapi.responses import HTMLResponse
from sqlite3 import Connection
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.io as pio

import re
import random


class User:
    def __init__(self, session_token: str, current_plots: list, time_frame: int, anchor_time: datetime):
        self.session_token = session_token
        self.current_plots = current_plots
        self.time_frame = time_frame
        self.anchor_time = anchor_time


class Tag:
    def __init__(self, id: str, data: pd.DataFrame | float, color: str):
        self.id = id
        self.data = data
        self.color = color

    #utility fxn, not using it to create an instance, so use @staticmethod
    @staticmethod
    def get_color() -> str:
            #professional color palette for data visualization
            colors = [
                '#0066cc',  # Primary blue
                '#0d9488',  # Teal
                '#7c3aed',  # Violet
                '#ea580c',  # Orange
                '#0891b2',  # Cyan
                '#4f46e5',  # Indigo
                '#059669',  # Emerald
                '#dc2626',  # Red
                '#2563eb',  # Blue
                '#7c2d12',  # Brown
                '#9333ea',  # Purple
                '#15803d',  # Green
            ]
            return random.choice(colors)

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
            
        #configure the plot with light professional theme
        fig.update_layout(
            template="plotly_white",
            paper_bgcolor='#ffffff',
            plot_bgcolor='#ffffff',
            font=dict(
                family="IBM Plex Sans, -apple-system, BlinkMacSystemFont, sans-serif",
                color='#334155',
                size=12
            ),
            title=dict(
                text=f"<b>{self.id}</b>",
                font=dict(size=14, color='#0f172a'),
                x=0.02,
                xanchor='left'
            ),
            xaxis=dict(
                gridcolor='#e2e8f0',
                showgrid=True,
                gridwidth=1,
                zeroline=False,
                tickformat='%m/%d %H:%M',
                tickfont=dict(size=11, color='#64748b'),
                linecolor='#e2e8f0',
                showline=True,
                mirror=False
            ),
            yaxis=dict(
                gridcolor='#e2e8f0',
                showgrid=True,
                gridwidth=1,
                zeroline=False,
                tickformat='.3g',
                tickfont=dict(size=11, color='#64748b'),
                linecolor='#e2e8f0',
                showline=True,
                mirror=False
            ),
            margin=dict(l=60, r=24, t=48, b=48),
            hovermode='x unified',
            hoverlabel=dict(
                bgcolor='#0f172a',
                font_size=12,
                font_family="IBM Plex Mono, monospace",
                font_color='#ffffff'
            )
        )
        #format hover tooltips to show 3 significant figures
        fig.update_traces(hovertemplate='%{x}<br>%{y:.3g}<extra></extra>')

        return pio.to_html(fig, config={'responsive': True})
