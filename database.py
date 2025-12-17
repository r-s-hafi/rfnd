from sqlite3 import Connection
from matplotlib import _preprocess_data
import pandas as pd
from fastapi.responses import HTMLResponse
import plotly.express as px
import plotly.io as pio
from datetime import datetime, timedelta

#creates process data database and populates with data from data.csv
def initialize_db(con: Connection) -> None:
    try:
        #read the data.csv file into a pandas dataframe
        df = pd.read_csv("data.csv")

        #insert the data into the database
        df.to_sql("process_data", con, if_exists="replace", index=False)

        #print the data from the database, currently just a test
        with con:
            cur = con.cursor()
            res = cur.execute("SELECT * FROM process_data")
    
    except Exception as e:
        print(f"Unable to import data: {e}")

def initialize_preferences(con: Connection) -> None:
    try:
        with con:
            cur = con.cursor()
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS preferences(
                        time_frame int,
                        anchor_time datetime
                        )""")
            con.commit()

            #check if preferences already exist
            cur.execute("SELECT 1 FROM preferences where time_frame is not null")
            exists = cur.fetchone()
            
            #only insert if table is empty
            if not exists:
                #set default time frame to 1 week and anchor time to current time
                cur.execute("INSERT INTO preferences (time_frame, anchor_time) VALUES (?, ?)", 
                           (60, datetime.now().replace(microsecond=0)))


    except Exception as e:
        print(f"Unable to initialize user preferences: {e}")

def update_preferences(con: Connection, time_frame: float) -> None:
    try:
        with con:
            cur = con.cursor()
            # Update all rows (should only be one row based on initialize_preferences)
            cur.execute("UPDATE preferences SET time_frame = ?, anchor_time = ?", (time_frame, datetime.now().replace(microsecond=0)))
            con.commit()

    except Exception as e:
        print(f"Unable to update user preferences: {e}")

#plots data for given tag id and returns html
def generate_plots(con_data: Connection, preference_data: Connection, tag_id: str, current_plots: list) -> HTMLResponse:
    #initialize string to store html for all plots
    wrapped_html = ""
    stored_plot_html = ""

    #get time frame from preferences
    with preference_data:
        cur = preference_data.cursor()
        cur.execute("SELECT time_frame FROM preferences")
        time_frame = cur.fetchone()[0]
        cur.execute("SELECT anchor_time FROM preferences")
        anchor_time = cur.fetchone()[0]


    print(f"Time frame: {time_frame}")
    print(f"Anchor time: {anchor_time}")

    end_time = datetime.strptime(anchor_time, "%Y-%m-%d %H:%M:%S")
    start_time = end_time - timedelta(minutes=time_frame)
    print(start_time)

    if tag_id != 'None':
        #generate html for queried tag id
        df = pd.read_sql(f"""SELECT Time, {tag_id}
                        FROM process_data
                        WHERE Time >= ? AND Time <= ? AND {tag_id} IS NOT NULL""", con_data, params=(start_time, end_time))
        fig = px.line(df, x="Time", y=tag_id, title=f"{tag_id}", labels={'Time': 'Time', tag_id: 'Value'})

        #configure the plot to be dark mode with better contrast
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor='#1c2128',
            plot_bgcolor='#0d1117',
            font=dict(color='#c9d1d9', size=12),
            title_font=dict(size=16, color='#e6edf3'),
            xaxis=dict(
                gridcolor='#30363d',
                showgrid=True,
                zeroline=False
            ),
            yaxis=dict(
                gridcolor='#30363d',
                showgrid=True,
                zeroline=False
            ),
            margin=dict(l=60, r=40, t=60, b=50),
            hovermode='x unified'
        )
        
        # Make the line more visible
        fig.update_traces(line=dict(width=2.5))

        plot_html = pio.to_html(fig, config={'responsive': True})     
        wrapped_html += f'<div id="plot">{plot_html}</div>'

    #generate html for all tags currently plotted
    print(f"Current plots: {current_plots}")
    for stored_tags in current_plots:

        if stored_tags != tag_id:
            df = pd.read_sql(f"""SELECT Time, {stored_tags}
                    FROM process_data
                    WHERE Time >= ? AND Time <= ? AND {stored_tags} IS NOT NULL""", con_data, params=(start_time, end_time))
            fig = px.line(df, x="Time", y=stored_tags, title=f"{stored_tags}", labels={'Time': 'Time', stored_tags: 'Value'})
            
            #configure the plot to be dark mode with better contrast
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor='#1c2128',
                plot_bgcolor='#0d1117',
                font=dict(color='#c9d1d9', size=12),
                title_font=dict(size=16, color='#e6edf3'),
                xaxis=dict(
                    gridcolor='#30363d',
                    showgrid=True,
                    zeroline=False
                ),
                yaxis=dict(
                    gridcolor='#30363d',
                    showgrid=True,
                    zeroline=False
                ),
                margin=dict(l=60, r=40, t=60, b=50),
                hovermode='x unified'
            )
            
            # Make the line more visible
            fig.update_traces(line=dict(width=2.5))

            stored_plot_html = pio.to_html(fig, config={'responsive': True})
            wrapped_html += f'<div id="plot">{stored_plot_html}</div>'

    return wrapped_html

