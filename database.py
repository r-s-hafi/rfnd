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
def generate_plots(con_data: Connection, con_preferences: Connection, current_plots: list) -> HTMLResponse:
    #initialize string to store html for all plots
    wrapped_html = ""
    stored_plot_html = ""

    #get time frame from preferences
    with con_preferences:
        cur = con_preferences.cursor()
        cur.execute("SELECT time_frame FROM preferences")
        time_frame = cur.fetchone()[0]
        cur.execute("SELECT anchor_time FROM preferences")
        anchor_time = cur.fetchone()[0]


    print(f"Time frame: {time_frame}")
    print(f"Anchor time: {anchor_time}")

    end_time = datetime.strptime(anchor_time, "%Y-%m-%d %H:%M:%S")
    start_time = end_time - timedelta(minutes=time_frame)

    for tag_id in current_plots:

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
        stored_plot_html = pio.to_html(fig, config={'responsive': True})
        wrapped_html += f'<div id="plot">{stored_plot_html}</div>'

    return wrapped_html

def update_anchor_time(con_data: Connection, con_preferences: Connection, operation: str) -> None:
    #update the anchor time to be the oldest point + current time frame
    if operation == "go_back":
        try:
            with con_data:
                cur = con_data.cursor()

                #find the oldest entry in the process data database
                cur.execute("""SELECT MIN(Time)
                            FROM process_data
                """)
            first_point = cur.fetchone()[0]
            first_point = datetime.strptime(first_point, "%Y-%m-%d %H:%M:%S")
            
            #update anchor point to be the oldest point + the current timeframe
            with con_preferences:
                cur = con_preferences.cursor()
                cur.execute("SELECT * FROM preferences where time_frame is not null")
                time_frame = cur.fetchone()[0]

                #make the new anchor point the oldest point in the database + the current time frame
                print(f'this is the first point {first_point}')
                print(f'this is the timedelta: {timedelta(minutes=time_frame)}')
                new_anchor = first_point + timedelta(minutes=time_frame)
                print(f'this is the new anchor: {new_anchor}')

                #update database with the new anchor point
                cur.execute("UPDATE preferences SET time_frame = ?, anchor_time = ?", (time_frame, new_anchor))
                
        except Exception as e:
            print(f"Unable to find oldest database entry: {e}")

    #update the anchor time to be the present time

    #this function is tricky when using CSV data as a placeholder like I am
    #in production this would just use datetime.now() as the new anchor time because the database should be constantly updating
    #but in CSV format when the data is updated intermittently, we will need to read the most recent data point and use that as our anchor point
    if operation == "go_present":
        try:
            with con_data:
                cur = con_data.cursor()

                #find the newest/most recent entry in the process data database
                cur.execute("""SELECT MAX(Time)
                            FROM process_data
                """)
            most_recent_point = cur.fetchone()[0]
            most_recent_point = datetime.strptime(most_recent_point, "%Y-%m-%d %H:%M:%S")
            
            #update anchor point to be the oldest point + the current timeframe
            with con_preferences:
                cur = con_preferences.cursor()
                cur.execute("SELECT * FROM preferences where time_frame is not null")
                time_frame = cur.fetchone()[0]

                #make the new anchor point the most recent point in the database
                print(f'this is the most recent point {most_recent_point}')
                print(f'this is the timedelta: {timedelta(minutes=time_frame)}')
                new_anchor = most_recent_point
                print(f'this is the new anchor: {new_anchor}')

                #update database with the new anchor point
                cur.execute("UPDATE preferences SET time_frame = ?, anchor_time = ?", (time_frame, new_anchor))
 
        except Exception as e:
            print(f"Unable to find oldest database entry: {e}")