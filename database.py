from sqlite3 import Connection
import pandas as pd
from fastapi.responses import HTMLResponse
from datetime import datetime, timedelta
import re
from models import Tag

#creates process data database and populates with data from data.csv
def initialize_db(con: Connection) -> None:
    try:
        #read the data.csv file into a pandas dataframe
        df = pd.read_csv("data.csv")

        #insert the data into the database (to_sql will create the table if it doesn't exist)
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

#return df object for given tag id
def get_df(con: Connection, tag_id: str) -> pd.DataFrame:
    try:
        #validate if df follows correct regex pattern
        if not re.match(r'^[a-zA-Z0-9_ ]+$', tag_id):
            return HTMLResponse(f"Invalid tag ID format.")
        
        #pd.read_sql to get a DataFrame directly
        #select Time and the tag_id column, filter where tag_id is not NULL
        df = pd.read_sql(f"SELECT Time, {tag_id} FROM process_data WHERE {tag_id} IS NOT NULL", con)
        return df
        
    except Exception as e:
        print(f"Unable to get df object for tag id: {e}")
        return None

#insert formula tag into database
def insert_new_tag(con: Connection, tag: Tag) -> None:
    try:
        
        with con:
            cur = con.cursor()
            #create new column with the new tag id
            cur.execute(f'ALTER TABLE process_data ADD COLUMN "{tag.id}" TEXT')
            updated_data = []

            #insert the value and rowid into updated data list
            #can introduce latency if there is a large amount of data, could be optimized more
            #if the result is a dataframe, insert the values into the database
            if isinstance(tag.data, pd.DataFrame):
                for i, value in enumerate(tag.data[tag.data.columns[1]]):
                    updated_data.append((value, i+1))

            #if the result is a constant, insert the value into the database for each entry in the time column
            elif isinstance(tag.data, float):
                with con:
                    cur = con.cursor()
                    cur.execute("""SELECT COUNT(*) FROM process_data""")
                    rows = cur.fetchone()[0]

                for i in range(rows):
                    updated_data.append((tag.data, i+1))

            #write the updated data to the database
            cur.executemany(f'UPDATE process_data SET "{tag.id}" = ? WHERE rowid = ?', updated_data)
            con.commit()

    except Exception as e:
        print(f"Unable to insert new tag into database: {e}")
            
#plots data for given tag id and returns html
def generate_plots(con_data: Connection, con_preferences: Connection, current_plots: list) -> HTMLResponse:
    #initialize string to store html for all plots
    wrapped_html = ""
    stored_plot_html = ""

    try:#get time frame from preferences
        with con_preferences:
            cur = con_preferences.cursor()
            cur.execute("SELECT time_frame FROM preferences")
            time_frame = cur.fetchone()[0]
            cur.execute("SELECT anchor_time FROM preferences")
            anchor_time = cur.fetchone()[0]

        end_time = datetime.strptime(anchor_time, "%Y-%m-%d %H:%M:%S")
        start_time = end_time - timedelta(minutes=time_frame)

        for tag in current_plots:

            stored_plot_html = Tag.plot(tag, con_data, start_time, end_time)
            wrapped_html += f'<div id="plot">{stored_plot_html}</div>'

    except Exception as e:
        print(f"Unable to generate plots: {e}")

    return wrapped_html

def update_anchor_time(con_data: Connection, con_preferences: Connection, operation: str) -> None:
    #update the anchor time to be the oldest point + current time frame
    if operation == "go_past":
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

    
    #update the anchor point to go backwards by the current timeframe
    if operation == "go_back":
        try: 
            with con_preferences:
                cur = con_preferences.cursor()
                cur.execute("SELECT * FROM preferences where time_frame is not null")
                #create dummy variable to store data from preference database
                preference_data = cur.fetchone()
                time_frame = preference_data[0]
                anchor_time = preference_data[1]

                print(f'time_frame = {time_frame}')
                print(f'anchor_time = {anchor_time}')

                #convert the anchor time into datetime object compatible with timedelta
                anchor_time = datetime.strptime(anchor_time, "%Y-%m-%d %H:%M:%S")

                #make the new anchor point the old one minus the amount of time specificed by the time frame
                new_anchor = anchor_time - timedelta(minutes=time_frame)

            #check if the user is trying to step previous to the oldest datapoint in the set
            #if so, set the anchor point to be the oldest point in the set + the current timeframe
            try:
                with con_data:
                    cur = con_data.cursor()

                    #find the oldest entry in the process data database
                    cur.execute("""SELECT MIN(Time)
                                    FROM process_data
                    """)
                    first_point = cur.fetchone()[0]
                    
                first_point = datetime.strptime(first_point, "%Y-%m-%d %H:%M:%S")

            except Exception as e:
                print(f"Unable to find oldest database entry: {e}")
                
            first_anchor = first_point + timedelta(minutes=time_frame)
                
            if new_anchor < first_anchor:
                print(f'''the oldest time point in the dataset is {first_point}, adding timeframe {time_frame}
                makes the oldest possible time frame {first_anchor}. Because the proposed new anchor {new_anchor} is 
                earlier in time than this oldest time frame, we are setting the new anchor to be {first_anchor}''')
                new_anchor = first_anchor

            with con_preferences:
                cur = con_preferences.cursor()
                #update database with the new anchor point
                cur.execute("UPDATE preferences SET time_frame = ?, anchor_time = ?", (time_frame, new_anchor))
            
        except Exception as e:
            print(f"Unable to step back: {e}")


    #update the anchor time to go forwards by the current time frame
    if operation == "go_forward":
        try: 
            with con_preferences:
                cur = con_preferences.cursor()
                cur.execute("SELECT * FROM preferences where time_frame is not null")
                #create dummy variable to store data from preference database
                preference_data = cur.fetchone()
                time_frame = preference_data[0]
                anchor_time = preference_data[1]

                print(f'time_frame = {time_frame}')
                print(f'anchor_time = {anchor_time}')

                #convert the anchor time into datetime object compatible with timedelta
                anchor_time = datetime.strptime(anchor_time, "%Y-%m-%d %H:%M:%S")

                #make the new anchor point the old one minus the amount of time specificed by the time frame
                new_anchor = anchor_time + timedelta(minutes=time_frame)

                #if the user tries to skip past the current time, set the anchor to the current time
                if new_anchor > datetime.now():
                    new_anchor = datetime.now().replace(microsecond=0)

                #update database with the new anchor point
                cur.execute("UPDATE preferences SET time_frame = ?, anchor_time = ?", (time_frame, new_anchor))
            
        except Exception as e:
            print(f"Unable to step forward: {e}")


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


def create_float_df(result: float, new_tag_id: str, con_data: Connection) -> pd.DataFrame:
    with con_data:
        cur = con_data.cursor()
        cur.execute("""SELECT MAX(TIME) FROM process_data""")
        max_time = cur.fetchone()[0]
        max_time = datetime.strptime(max_time, "%Y-%m-%d %H:%M:%S")
    rows = 1
    cols = [new_tag_id]
    return pd.DataFrame(data=np.full(rows, cols, result), columns=cols)

    
        
