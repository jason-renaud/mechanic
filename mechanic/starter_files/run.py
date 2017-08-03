import os
from app import create_app


config_name = os.getenv("FLASK_CONFIG")
port = os.getenv("FLASK_PORT")
app = create_app(config_name)

if __name__ == "__main__":
    if port:
        app.run(port=int(port))
    else:
        app.run()
