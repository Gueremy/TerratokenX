import sqlite3

conn = sqlite3.connect('reservation_project/data/db.sqlite3')
c = conn.cursor()
c.execute('SELECT id, total FROM booking_reserva WHERE total IS NULL OR total = ""')
print('Null or empty totals:', c.fetchall())

c.execute('SELECT id, total FROM booking_reserva')
all_records = c.fetchall()
print('All records:')
for r in all_records:
    print(f'  ID: {r[0]}, Total: {r[1]}, Type: {type(r[1])}')
