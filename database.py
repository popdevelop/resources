import sqlite3

DB_FILE = "database.db"

class Database():
    def __init__(self):
        self.statements = []
        self.connection = sqlite3.connect(DB_FILE)
        self.cursor = self.connection.cursor()

        self.add_statement('''create table if not exists stops (id INTEGER PRIMARY KEY, name STRING, lon FLOAT, lat FLOAT)''')

        self.commit()

    def add_statement(self, statement, args = []):
        self.statements.append((statement, args))

    def commit(self):
        map(lambda x: self.cursor.execute(x[0], x[1]), self.statements)
        self.connection.commit()
        self.statements = []

if __name__ == "__main__":
    import os
    os.remove(DB_FILE)
    db = Database()
