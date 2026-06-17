import sqlite3

def login(username, password):
  conn = sqlite3.connect("users.db")
  cursor = conn.cursor()
  query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
  cursor.execute(query)
  return cursor.fetchone()

login("admin", "1234")
