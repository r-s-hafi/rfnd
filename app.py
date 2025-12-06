from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates
import sqlite3

import plotly.express as p

from database import initialize_data_db, plot_tag_data, initialize_html_db, store_html, render_html

#create the fastapi instance, Jinja2 templates to return HTML, and initialize database
app = FastAPI()
templates = Jinja2Templates('./templates')
con_data = sqlite3.connect("process_data.db")
con_html = sqlite3.connect("plot_html.db")
#counter for number of plots
plot_count = 0
#list of tags currently plotted
current_plots = []

@app.get("/")
async def initialize(request: Request) -> HTMLResponse:
   #initialize database and populate with the data from the csv
   initialize_data_db(con_data)
   initialize_html_db(con_html)
   #return homepage "index.html"
   return templates.TemplateResponse(request, "index.html")

@app.post("/get-tag-id")
async def get_tag_id(request: Request, tag_id: str = Form()) -> HTMLResponse:
   #declare plot count and current plots as global variables
   global plot_count, current_plots
   tag_id = tag_id.upper()
   try:
      #call plot data to collect tag data and return html graph
      plot_html = plot_tag_data(con_data, tag_id)
      store_html(con_html, tag_id, plot_html)
   
   except Exception as e:
      return HTMLResponse(f"""
                        <h1>Error plotting data for tag {tag_id}</h1>
                        <p>{e}</p>
                        """)
   
   #check for repeat plots
   if tag_id in current_plots:
      print(f"Plot already exists for tag {tag_id}")
   
   else:
      #if try block runs, add plot count to html response
      current_plots.append(tag_id)
      plot_count += 1
      rendered_html = render_html(tag_id, con_html, current_plots)
      return HTMLResponse(f"""
                        <div id="plot-area" hx-swap-oob="true">
                           {rendered_html}
                        </div>
                        """)
