from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import sqlite3
from datetime import datetime

from database import initialize_db, generate_plots, initialize_preferences, update_preferences, update_anchor_time
from datamanipulation import detect_time_frame 
from formula_parse import parse_formula

#create the fastapi instance, connect CSS, Jinja2 templates to return HTML, and initialize databases
app = FastAPI()
templates = Jinja2Templates('./templates')
app.mount("/static", StaticFiles(directory="static"), name="static")

con_data = sqlite3.connect("process_data.db")
con_preferences = sqlite3.connect("preferences.db")

#counter for number of plots
plot_count = 0
#list of tags currently plotted
current_plots = []

#initializes database and global variables
@app.get("/")
async def initialize(request: Request) -> HTMLResponse:
   #initialize database and populate with the data from the csv\
   global current_plots
   current_plots = []
   initialize_db(con_data)
   initialize_preferences(con_preferences)
   #return homepage "index.html"
   return templates.TemplateResponse(request, "index.html")

#renders the formula documentation page
@app.get("/formula_docs")
async def formula_docs(request: Request) -> HTMLResponse:
   #return formula documentation page
   return templates.TemplateResponse(request, "formula_docs.html")

#accepts the tag ID from the user and re-generates all plots in current session
@app.post("/get-tag-id")
async def get_tag_id(tag_id: str = Form()) -> HTMLResponse:
   #declare plot count and current plots as global variables
   global plot_count, current_plots
   tag_id = tag_id.upper()

   #check for repeat plots
   if tag_id in current_plots:
      print(f"Plot already exists for tag {tag_id}")
   
   else:
      #if try block runs, add plot count to html response
      current_plots.append(tag_id)
      plot_count += 1

   try:
      #call plot data to collect tag data for queried tag and all other currently plotted tags
      plot_html = generate_plots(con_data, con_preferences, current_plots)
      return HTMLResponse(f"""
                     <div id="plot-area" hx-swap-oob="true"">
                        {plot_html}
                     </div>
                     <div id="current-tags-list" hx-swap-oob="true">
                        <ul>
                           {''.join(f'<button type="button" id="{tag_id}" name="tag_id" value="{tag_id}" hx-post="/insert-tag-into-formula" hx-include="#formula-input">{tag_id}</button>' for tag_id in current_plots)}
                        </ul>
                     </div>
                     """)
      
   except Exception as e:
      return HTMLResponse(f"""
                           <h1>Error plotting data for tag {tag_id}</h1>
                           <p>{e}</p>
                           """)

#updates the time frame for the current session
@app.post("/update-time-frame")
async def update_time_frame(time_frame: str = Form()) -> HTMLResponse:
   if time_frame:
      cleaned_time_frame = detect_time_frame(time_frame)
      if cleaned_time_frame:
         print(f"Time frame will beupdated to {cleaned_time_frame} minutes")
         
         #update the preferences database with the most recent anchor time and the desired time frame
         update_preferences(con_preferences, cleaned_time_frame)
         print(f"Current plots: {current_plots}")
         try:
            #call plot data to collect tag data for all currently plotted tags
            plot_html = generate_plots(con_data, con_preferences, current_plots)
            return HTMLResponse(f"""
                           <div id="plot-area" hx-swap-oob="true"">
                              {plot_html}
                           </div>
                           """)
      
         except Exception as e:
            return HTMLResponse(f"""
                           <h1>Error updating time frame</h1>
                           <p>{e}</p>
                           """)

         #this will adjust the time fram in the database
      else:
         print("please enter a valid time frame")
   else:
      print("please enter a time frame")

#moves the anchor time as far baack as possible given the current time frame
@app.post("/go-past")
async def go_past() -> HTMLResponse:
   update_anchor_time(con_data, con_preferences, "go_past")
   try:
      #call plot data to collect tag data for all currently plotted tags
      plot_html = generate_plots(con_data, con_preferences, current_plots)
      return HTMLResponse(f"""
                           <div id="plot-area" hx-swap-oob="true"">
                              {plot_html}
                           </div>
                           """)
      
   except Exception as e:
      return HTMLResponse(f"""
                           <h1>Error going to past</h1>
                           <p>{e}</p>
                           """)

#moves the anchor time backwards by the current time frame
@app.post("/go-back")
async def go_back() -> HTMLResponse:
   update_anchor_time(con_data, con_preferences, "go_back")
   try:
      #call plot data to collect tag data for all currently plotted tags
      plot_html = generate_plots(con_data, con_preferences, current_plots)
      return HTMLResponse(f"""
                           <div id="plot-area" hx-swap-oob="true"">
                              {plot_html}
                           </div>
                           """)
      
   except Exception as e:
      return HTMLResponse(f"""
                           <h1>Error going to past</h1>
                           <p>{e}</p>
                           """)

#moves the anchor time forwards by the current time frame
@app.post("/go-forward")
async def go_back() -> HTMLResponse:
   update_anchor_time(con_data, con_preferences, "go_forward")
   try:
      #call plot data to collect tag data for all currently plotted tags
      plot_html = generate_plots(con_data, con_preferences, current_plots)
      return HTMLResponse(f"""
                           <div id="plot-area" hx-swap-oob="true"">
                              {plot_html}
                           </div>
                           """)
      
   except Exception as e:
      return HTMLResponse(f"""
                           <h1>Error going to past</h1>
                           <p>{e}</p>
                           """)

#moves the anchor time to the present time
@app.post("/go-present")
async def go_past() -> HTMLResponse:
   update_anchor_time(con_data, con_preferences, "go_present")
   try:
      #call plot data to collect tag data for all currently plotted tags
      plot_html = generate_plots(con_data, con_preferences, current_plots)
      return HTMLResponse(f"""
                           <div id="plot-area" hx-swap-oob="true"">
                              {plot_html}
                           </div>
                           """)
      
   except Exception as e:
      return HTMLResponse(f"""
                           <h1>Error going to past</h1>
                           <p>{e}</p>
                           """)

#insert tag into formula
@app.post("/insert-tag-into-formula")
async def insert_tag_into_formula(tag_id: str = Form(), operation: str = Form(default="")) -> HTMLResponse:
   new_formula = operation + tag_id
   return HTMLResponse(f"""
                           <div id="formula-input-container" hx-swap-oob="true">
                              <form id="formula-form" hx-trigger="submit" hx-target="#plot-area">
                                 <input type="text" id="formula-input" name="operation" class="input" placeholder="Enter formula" value="{new_formula}">
                              </form>
                           </div>

                           <div id="current-tags-list" hx-swap-oob="true">
                              <ul>
                                 {''.join(f'<button type="button" id="{tag_id}" name="tag_id" value="{tag_id}" hx-post="/insert-tag-into-formula" hx-include="#formula-input">{tag_id}</button>' for tag_id in current_plots)}
                              </ul>
                           </div>
                        """)

#execute formula by pasing and running appropriate operations functions
@app.post("/execute-formula")
async def execute_formula(formula: str = Form()) -> HTMLResponse:
   tags, operations = parse_formula(formula)


