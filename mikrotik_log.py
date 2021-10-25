import sqlite3
from sqlite3 import Error
import socketserver
from datetime import datetime
import pytz

HOST = '0.0.0.0'
PORT = 3514

dbConnection = sqlite3.connect('mikrotik_log_db.db', check_same_thread = False)



def create_log(conn, log_data):
  sql = "INSERT INTO log (date, message) VALUES (?, ?)"
  cur = conn.cursor()
  cur.execute(sql, log_data)
  conn.commit()
  return cur.lastrowid

def create_log_topic(conn, log_data):
  sql = "INSERT INTO log_topic (log_id, topic) VALUES (?, ?)"
  cur = conn.cursor()
  cur.execute(sql, log_data)
  conn.commit()
  return cur.lastrowid

def create_log_socket(conn, log_data):
  sql = "INSERT INTO log_socket (log_id, address, port) VALUES (?, ?, ?)"
  cur = conn.cursor()
  cur.execute(sql, log_data)
  conn.commit()
  return cur.lastrowid



class SyslogUDPHandler(socketserver.BaseRequestHandler):
  def handle(self):
    data = bytes.decode(self.request[0].strip()).split(" ", 1)
    topics = data[0].split(",")
    message = data[1]
    tz_Ala = pytz.timezone('Asia/Almaty') 
    now = datetime.now(tz_Ala)
    address = self.client_address[0]
    port = self.client_address[1]

    logId = create_log(dbConnection, (now, message))
    for topic in topics:
      create_log_topic(dbConnection, (logId, topic))
    create_log_socket(dbConnection, (logId, address, port))

    print(address, data)


if __name__ == "__main__":
  try:
    server = socketserver.UDPServer((HOST, PORT), SyslogUDPHandler)
    server.serve_forever(poll_interval = 0.5)
  except (IOError, SystemExit):
    raise
  except KeyboardInterrupt:
    print ("Crtl+C Pressed. Shutting down.")