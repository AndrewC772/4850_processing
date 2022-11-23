import sqlite3

conn = sqlite3.connect('stats.sqlite')

c = conn.cursor()
c.execute('''
          CREATE TABLE events
          (id INTEGER PRIMARY KEY ASC,
           num_devices INTEGER NOT NULL,
           max_device_latency INTEGER NOT NULL,
           num_networks INTEGER NOT NULL,
           max_network_device_count INTEGER NOT NULL,
           last_update VARCHAR(100) NOT NULL)
          ''')

conn.commit()
conn.close()
