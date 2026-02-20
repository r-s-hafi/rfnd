from fastapi import FastAPI, Form, Cookie
from fastapi.responses import HTMLResponse
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from datetime import datetime

import pandas as pd
import numpy as np

import sqlite3
import re

from models import User, Tag
from database import initialize_db, generate_plots, update_preferences, update_anchor_time, insert_new_tag
from utility import detect_time_frame, handle_cookie, check_cookie
from parser import parse_formula

#create the fastapi instance, connect CSS, Jinja2 templates to return HTML, and initialize databases
app = FastAPI()
templates = Jinja2Templates('./templates')
app.mount("/static", StaticFiles(directory="static"), name="static")

con_data = sqlite3.connect("process_data.db")

#dictionary to store user sessions
user_sessions = {}

#initializes database and global variables
@app.get("/")
async def initialize(request: Request, session_token: str = Cookie(None)) -> HTMLResponse:

   #checks if there is a user session in the cookie, if not creates uuid and adds to user_sessions
   session_token, is_new_user = handle_cookie(session_token, user_sessions)
   
   if is_new_user:
      #create user object
      user = User(session_token, current_plots = [], time_frame = 60, anchor_time = datetime.now().replace(microsecond=0))
      user_sessions[session_token] = user
   else:
      user = user_sessions[session_token]   

   response = templates.TemplateResponse(request, "index.html", {"text": ""})

   #set the cookies in the users browser
   response.set_cookie(
      key="session_token",
      value = session_token,
      max_age = 86400,
      httponly = True,
   )

   #initialize database and populate with the data from the csv
   initialize_db(con_data)

   
   return response

#renders the formula documentation page
@app.get("/formula_docs")
async def formula_docs(request: Request) -> HTMLResponse:
   #return formula documentation page
   return templates.TemplateResponse(request, "formula_docs.html")

#returns available tags in the database for the sidebar browser
@app.get("/get-available-tags")
async def get_available_tags() -> HTMLResponse:
   try:
      with con_data:
         cur = con_data.cursor()
         #get column names from the process_data table (excluding Time)
         cur.execute("PRAGMA table_info(process_data)")
         columns = cur.fetchall()
         tags = [col[1] for col in columns if col[1] != 'Time']

      #generate HTML for the tag list
      tag_html = ""
      for tag in tags:
         tag_html += f'''
            <button class="tag-item"
                    hx-post="/get-tag-id"
                    hx-target="#trend-area"
                    hx-vals='{{"tag_id": "{tag}"}}'>
               <span class="tag-item-icon"></span>
               <span class="tag-item-name">{tag}</span>
               <span class="tag-item-type">Signal</span>
            </button>'''

      #update the tag count
      count_html = f'''
         <span class="tag-count" id="available-tag-count" hx-swap-oob="true">{len(tags)}</span>
      '''

      return HTMLResponse(tag_html + count_html)

   except Exception as e:
      return HTMLResponse(f'<div class="tag-item">Error loading tags: {e}</div>')

#accepts the tag ID from the user and re-generates all plots in current session
@app.post("/get-tag-id")
async def get_tag_id(tag_id: str = Form(), session_token: str = Cookie(None)) -> HTMLResponse:
   
   #check cookie
   if check_cookie(session_token, user_sessions):
      user = user_sessions[session_token]
   else:
      return HTMLResponse(f"Session not found")
   

   #validate tag.id to prevent SQL injection
   #only allow alphanumeric characters, underscores (SQLite identifiers)
   #no spaces allowed for non-user created tags
   if not re.match(r'^[a-zA-Z0-9_]+$', tag_id):
      return HTMLResponse(f"Invalid tag ID format.")

   else:
      tag = Tag(str(tag_id).upper(), None, Tag.get_color() )

      #check for repeat plots
      existing_tag_ids = [tag.id for tag in user.current_plots]
      if tag.id in existing_tag_ids:
         print(f"Plot already exists for tag {tag.id}")
      
      else:
         #if try block runs, add plot count to html response
         user.current_plots.append(tag)

      try:
         #call plot data to collect tag data for queried tag and all other currently plotted tags
         plot_html = generate_plots(con_data, user)
         tag_id = tag.id
         return HTMLResponse(f"""
                        <div id="trend-area" hx-swap-oob="true">
                           {plot_html}
                        </div>
                        <div id="current-tags-list" hx-swap-oob="true">
                           {''.join(f'<button type="button" class="active-tag" id="{tag.id}" name="tag_id" value="{tag.id}" hx-post="/insert-tag-into-formula" hx-include="#formula-input">{tag.id}</button>' for tag in user.current_plots)}
                        </div>
                        """)
         
      except Exception as e:
         return HTMLResponse(f"""
                              <h1>Error plotting data for tag {tag_id}</h1>
                              <p>{e}</p>
                              """)

#updates the time frame for the current session
@app.post("/update-time-frame")
async def update_time_frame(time_frame: str = Form(), session_token: str = Cookie(None)) -> HTMLResponse:
   
   #check cookie
   if check_cookie(session_token, user_sessions):
      user = user_sessions[session_token]
   else:
      return HTMLResponse(f"Session not found")
   
   if time_frame:
      cleaned_time_frame = detect_time_frame(time_frame)
      if cleaned_time_frame:
         print(f"Time frame will beupdated to {cleaned_time_frame} minutes")
         
         #update the user preferences with the desired time frame
         update_preferences(cleaned_time_frame, user)

         try:
            #call plot data to collect tag data for all currently plotted tags
            plot_html = generate_plots(con_data, user)
            return HTMLResponse(f"""
                           <div id="trend-area" hx-swap-oob="true">
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
async def go_past(session_token: str = Cookie(None)) -> HTMLResponse:
   
   #check cookie
   if check_cookie(session_token, user_sessions):
      user = user_sessions[session_token]
   else:
      return HTMLResponse(f"Session not found")
   
   update_anchor_time(con_data, user, "go_past")
   try:
      #call plot data to collect tag data for all currently plotted tags
      plot_html = generate_plots(con_data, user)
      return HTMLResponse(f"""
                           <div id="trend-area" hx-swap-oob="true">
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
async def go_back(session_token: str = Cookie(None)) -> HTMLResponse:
   
   #check cookie
   if check_cookie(session_token, user_sessions):
      user = user_sessions[session_token]
   else:
      return HTMLResponse(f"Session not found")
   
   update_anchor_time(con_data, user, "go_back")
   try:
      #call plot data to collect tag data for all currently plotted tags
      plot_html = generate_plots(con_data, user)
      return HTMLResponse(f"""
                           <div id="trend-area" hx-swap-oob="true">
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
async def go_back(session_token: str = Cookie(None)) -> HTMLResponse:
   
   #check cookie
   if check_cookie(session_token, user_sessions):
      user = user_sessions[session_token]
   else:
      return HTMLResponse(f"Session not found")
   
   update_anchor_time(con_data, user, "go_forward")
   try:
      #call plot data to collect tag data for all currently plotted tags
      plot_html = generate_plots(con_data, user)
      return HTMLResponse(f"""
                           <div id="trend-area" hx-swap-oob="true">
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
async def go_past(session_token: str = Cookie(None)) -> HTMLResponse:
   
   #check cookie
   if check_cookie(session_token, user_sessions):
      user = user_sessions[session_token]
   else:
      return HTMLResponse(f"Session not found")
   
   update_anchor_time(con_data, user, "go_present")
   try:
      #call plot data to collect tag data for all currently plotted tags
      plot_html = generate_plots(con_data, user)
      return HTMLResponse(f"""
                           <div id="trend-area" hx-swap-oob="true">
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
async def insert_tag_into_formula(tag_id: str = Form(), formula: str = Form(default=""), session_token: str = Cookie(None)) -> HTMLResponse:
   
   #check cookie
   if check_cookie(session_token, user_sessions):
      user = user_sessions[session_token]
   else:
      return HTMLResponse(f"Session not found")
   
   new_formula = formula + tag_id
   return HTMLResponse(f"""
                           <textarea id="formula-input"
                                     name="formula"
                                     class="formula-textarea"
                                     placeholder="Enter formula (e.g., PI001 + TI001)"
                                     rows="3"
                                     hx-swap-oob="true">{new_formula}</textarea>
                           <div id="current-tags-list" hx-swap-oob="true">
                              {''.join(f'<button type="button" class="active-tag" id="{tag.id}" name="tag_id" value="{tag.id}" hx-post="/insert-tag-into-formula" hx-include="#formula-input">{tag.id}</button>' for tag in user.current_plots)}
                           </div>
                        """)

#execute formula by pasing and running appropriate operations functions
@app.post("/execute-formula")
async def execute_formula(formula: str = Form(), new_tag_id: str = Form(), session_token: str = Cookie(None)) -> HTMLResponse:
   
   #check cookie
   if check_cookie(session_token, user_sessions):
      user = user_sessions[session_token]
   else:
      return HTMLResponse(f"Session not found")

   #if no tag ID specified, return warning
   if not new_tag_id:
      return HTMLResponse(f"""
                           <div id="new-tag-warning" hx-swap-oob="true">
                              <p>Please enter a new tag ID</p>
                           </div>
                           """)
   #parse the formula entered by the user, perform the operations, and insert the new tag into the database
   else:
      try: 
         #returns df object with operations performed
         result = parse_formula(formula)

         #rename the column to the new tag ID if the result is a dataframe, if the result is a const, no operation is necessary
         if isinstance(result, pd.DataFrame):
            result = result.rename(columns={result.columns[1]: new_tag_id})

         #validate new tag ID to prevent SQL injection
         #only allow alphanumeric characters, underscores, and spaces (SQLite identifiers)
         #spaces allowed for user-created formulas
         if not re.match(r'^[a-zA-Z0-9_ ]+$', new_tag_id):
            return HTMLResponse(f"Invalid tag ID format.")

         else:
            tag = Tag(str(new_tag_id), result, Tag.get_color())

            #insert the new tag into the database, creates a tag object as well
            insert_new_tag(con_data, tag)

            #new tag id is succesfully inserted into the database, add to current plots and plot count
            existing_tag_ids = [tag.id for tag in user.current_plots]
            if tag.id not in existing_tag_ids:
               user.current_plots.append(tag)

            #replot all data with new tag
            try:
               plot_html = generate_plots(con_data, user)
               return HTMLResponse(f"""
                                 <div id="trend-area" hx-swap-oob="true">
                                    {plot_html}
                                 </div>
                                 <div id="current-tags-list" hx-swap-oob="true">
                                    {''.join(f'<button type="button" class="active-tag" id="{tag.id}" name="tag_id" value="{tag.id}" hx-post="/insert-tag-into-formula" hx-include="#formula-input">{tag.id}</button>' for tag in user.current_plots)}
                                 </div>
                                 <div id="new-tag-warning" hx-swap-oob="true">
                                 </div>
                                 """)
                  
            except Exception as e:
                  return HTMLResponse(f"""
                                       <h1>Error plotting data for tag {tag.id}</h1>
                                       <p>{e}</p>
                                       """)
      except Exception as e:
         return HTMLResponse(f"""
                           <div id="new-tag-warning" hx-swap-oob="true">
                              <p>Error parsing formula: {e}</p>
                           </div>
                           """)



