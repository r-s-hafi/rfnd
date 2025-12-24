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
        
        value_TI001 = 995
        value_PI001 = 120
        rands = [1, 2]
        row_entry = []
        #add the data rows
        for i in range(num_minutes):
            time = datetime.now().replace(microsecond=0) - timedelta(minutes=i)

            num = random.choice(rands)

            if num == 1:
                value_TI001 -= 0.1
                value_PI001 += 0.1
            else:
                value_TI001 += 0.1
                value_PI001 -= 0.1
            
            row_entry.append(time)
            row_entry.append(value_TI001)
            row_entry.append(value_PI001)
            writer.writerow(row_entry)
            row_entry.clear()


generate_process_data(100000)