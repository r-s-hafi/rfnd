from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import sqlite3

import plotly.express as p

from database import initialize_db, generate_plots, initialize_preferences

#create the fastapi instance, connect CSS, Jinja2 templates to return HTML, and initialize databases
app = FastAPI()
templates = Jinja2Templates('./templates')
app.mount("/static", StaticFiles(directory="static"), name="static")

con_data = sqlite3.connect("process_data.db")
preference_data = sqlite3.connect("preferences.db")

#counter for number of plots
plot_count = 0
#list of tags currently plotted
current_plots = []

@app.get("/")
async def initialize(request: Request) -> HTMLResponse:
   #initialize database and populate with the data from the csv
   initialize_db(con_data)
   initialize_preferences(preference_data)
   #return homepage "index.html"
   return templates.TemplateResponse(request, "index.html")

@app.post("/get-tag-id")
async def get_tag_id(tag_id: str = Form()) -> HTMLResponse:
   #declare plot count and current plots as global variables
   global plot_count, current_plots
   tag_id = tag_id.upper()
   try:
      #call plot data to collect tag data for queried tag and all other currently plotted tags
      plot_html = generate_plots(con_data, tag_id, current_plots)
   
   except Exception as e:
      return HTMLResponse(f"""
                        <h1>Error plotting data for tag {tag_id}</h1>
                        <p>{e}</p>
                        """)
   
   current_plots.clear()
   
   #check for repeat plots
   if tag_id in current_plots:
      print(f"Plot already exists for tag {tag_id}")
   
   else:
      #if try block runs, add plot count to html response
      current_plots.append(tag_id)
      plot_count += 1
      return HTMLResponse(f"""
                        <div id="plot-area" hx-swap-oob="true"">
                           {plot_html}
                        </div>
                        """)

@app.post("/update-time-frame")
async def update_time_frame(request: Request, time_frame: str = Form()) -> HTMLResponse:
   pass