#! /usr/bin/python3

import csv

repetitions = {{ repetitions }}

rates = []
for rep in range(1, repetitions + 1):
    with open('throughput-max-rx.csv_{}'.format(str(rep)), 'r') as fh:
        reader = csv.DictReader(fh, delimiter=',')
        max_row = next(reader)
        compare = 'PacketRate'
        for row in reader:
            if row[compare] > max_row[compare]:
                max_row = row
        # print(','.join(list(max_row.values())[3:6]))
        max_rate = float(max_row[compare]) * 1000000
        rates.append(max_rate)
print(max(rates))
