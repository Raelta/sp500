import csv

input_file = 'SP.csv'
output_file = 'SP_last_10_years.csv'
# Cutoff date: 10 years before the last date in the file (2026/01/29)
cutoff_date = '2016/01/29'

print(f"Starting extraction from {input_file} to {output_file}...")
print(f"Cutoff date: {cutoff_date}")

try:
    with open(input_file, mode='r', newline='') as infile:
        reader = csv.reader(infile)
        header = next(reader)
        
        with open(output_file, mode='w', newline='') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(header)
            
            count = 0
            found_start = False
            for row in reader:
                # Column index 2 is 'Date'
                if not found_start:
                    if row[2] >= cutoff_date:
                        found_start = True
                        writer.writerow(row)
                        count += 1
                else:
                    # Once we've found the start, we assume it's sorted and write everything
                    writer.writerow(row)
                    count += 1
                
                if count % 1000000 == 0 and count > 0:
                    print(f"Processed {count} rows...")

    print(f"Extraction complete. Total rows written: {count}")

except FileNotFoundError:
    print(f"Error: {input_file} not found.")
except Exception as e:
    print(f"An error occurred: {e}")
