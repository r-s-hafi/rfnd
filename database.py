from sqlite3 import Connection
import pandas as pd
from fastapi.responses import HTMLResponse
import plotly.express as px
import plotly.io as pio

#creates process data database and populates with data from data.csv
def initialize_data_db(con: Connection) -> None:
    try:
        #read the data.csv file into a pandas dataframe
        df = pd.read_csv("data.csv")

        #insert the data into the database
        df.to_sql("process_data", con, if_exists="replace", index=False)

        #print the data from the database, currently just a test
        with con:
            cur = con.cursor()
            res = cur.execute("SELECT * FROM process_data")
            print(res.fetchall())
    
    except Exception as e:
        print(f"Unable to import data: {e}")

#creates html database
def initialize_html_db(con: Connection) -> None:
    try:
        #create a new table in the database
        con.execute("CREATE TABLE IF NOT EXISTS plot_html (tag_id TEXT, html TEXT)")
    
    except Exception as e:
        print(f"Unable to initialize HTML database: {e}")

#plots data for given tag id and returns html
def plot_tag_data(con: Connection, tag_id: str) -> HTMLResponse:
    tag_id = tag_id.upper()
    df = pd.read_sql(f"SELECT Time, {tag_id} FROM process_data", con)
    fig = px.line(df, x="Time", y=tag_id, title=f"{tag_id}", labels={'Time': 'Time', tag_id: 'Value'})
    plot_html = pio.to_html(fig)     
    return plot_html

#stores html for given tag id
def store_html(con: Connection, tag_id: str, html: str) -> None:
    try:
        wrapped_html = f'<div id="plot">{html}</div>'
        with con:
            cur = con.cursor()
            cur.execute("INSERT INTO plot_html VALUES (?, ?)", (tag_id, wrapped_html))
    except Exception as e:
        print(f"Unable to write html to HTML database: {e}")

def render_html(tag_id: str, con: Connection, current_plots: list) -> str:
    rendered_html = ""
    for tag_id in current_plots:
        try:
            with con:
                cur = con.cursor()
                cur.execute(f"SELECT html FROM plot_html WHERE tag_id = '{tag_id}'")
                html = cur.fetchone()
                if html:
                    html = html[0]
                    rendered_html += html
                    print(f"successfully rendered html for tag {tag_id}")
        
        except Exception as e:
            print(f"Unable to render html for tag {tag_id}: {e}")
            continue
    return rendered_html