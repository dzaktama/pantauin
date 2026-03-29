import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
app = create_app()

print("Registered Routes:")
for rule in app.url_map.iter_rules():
    print(f"{rule.endpoint}: {rule}")
