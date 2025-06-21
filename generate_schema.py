from flask import Flask
from sqlalchemy.schema import CreateTable
from database import db, init_db, User, PasswordHistory

app = Flask(__name__)
init_db(app)

def generate_schema():
    with app.app_context():
        with open("schema.sql", "w") as f:
            for table in db.metadata.sorted_tables:
                ddl = str(CreateTable(table).compile(db.engine))
                f.write(f"{ddl};\n\n")
                print(f"Generated SQL for table: {table.name}")
                print(ddl)
                print("\n")

if __name__ == '__main__':
    generate_schema() 