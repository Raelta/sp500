import csv

input_file = 'SP.csv'
output_file = 'SP_25yr_1min.csv'
# Cutoff date: 25 years before the last date in the file (2026/01/29)
cutoff_date = '2001/01/29'

print(f"Starting extraction from {input_file} to {output_file}...")
print(f"Cutoff date: {cutoff_date}")
print("Filtering for 1-minute samples...")

try:
    with open(input_file, mode='r', newline='') as infile:
        reader = csv.reader(infile)
        header = next(reader)
        
        with open(output_file, mode='w', newline='') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(header)
            
            count = 0
            found_start = False
            last_minute = None # Format: "YYYY/MM/DD HH:MM"
            
            for row in reader:
                # Column index 2 is 'Date', index 3 is 'Time'
                # row[2] format: "YYYY/MM/DD"
                # row[3] format: "HH:MM:SS.mmm"
                
                date_val = row[2]
                
                if not found_start:
                    if date_val >= cutoff_date:
                        found_start = True
                
                if found_start:
                    # Extract minute: HH:MM
                    time_val = row[3]
                    current_minute = f"{date_val} {time_val[:5]}" # Take "YYYY/MM/DD" and "HH:MM"
                    
                    if current_minute != last_minute:
                        writer.writerow(row)
                        last_minute = current_minute
                        count += 1
                
                if count > 0 and count % 100000 == 0:
                    # Logging every 100k written rows (which represent minutes now)
                    # We can also track progress by lines read if we wanted to
                    pass

    print(f"Extraction complete. Total 1-minute samples written: {count}")

except FileNotFoundError:
    print(f"Error: {input_file} not found.")
except Exception as e:
    print(f"An error occurred: {e}")
