from datetime import datetime, timedelta
import random
import csv

def generate_process_data(num_minutes: int) -> None:
    #add headers to csv (time and all of the tags)
    tags = ["Time", "TI001", "PI001"]
    
    with open("data.csv", "w") as f:
        writer = csv.writer(f)
        #add the headers row
        writer.writerow(tags)
        
        row_entry = []
        #add the data rows
        for i in range(num_minutes):
            time = datetime.now().replace(microsecond=0) - timedelta(minutes=i)
            value_TI001 = random.randint(900, 1005)
            value_PI001 = random.randint(90, 150)
            row_entry.append(time)
            row_entry.append(value_TI001)
            row_entry.append(value_PI001)
            writer.writerow(row_entry)
            row_entry.clear()


generate_process_data(100000)