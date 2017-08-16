import os
import threading

from flask import render_template

from base.messaging import Listener
from app import create_app


config_name = os.getenv("FLASK_CONFIG")
if not config_name:
    print("FLASK_CONFIG environment variable not defined. Set to 'development' or 'testing' or 'production'")
    exit()

port = os.getenv("FLASK_PORT")
if not port:
    print("FLASK_PORT environment variable not defined, using default port 5000")

app, socketio = create_app(config_name)


# register the home route
@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    # register all listeners
    # TODO - figure out how to properly handle threads here
    for item in Listener.__subclasses__():
        listener = item(rabbit_url="http://localhost")
        t = threading.Thread(target=listener.run)
        t.start()

    if port:
        socketio.run(app, port=int(port))
    else:
        socketio.run(app)
