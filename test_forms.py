import traceback
from flask import Flask
app = Flask(__name__)
app.config['WTF_CSRF_ENABLED'] = False
try:
    with app.app_context():
        from forms import ProfilPerusahaanForm
        from werkzeug.datastructures import MultiDict
        f=ProfilPerusahaanForm(formdata=MultiDict())
        print("FORMS_OK")
except Exception as e:
    traceback.print_exc()
