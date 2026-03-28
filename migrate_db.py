# pyre-ignore-all-errors
from app import create_app
from models import db, AktivitasLog

app = create_app()

with app.app_context():
    db.create_all()
    print("Database migration completed: aktivitas_log created.")
