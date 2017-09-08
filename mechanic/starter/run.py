import os
from app import create_app


config_name = os.getenv("FLASK_CONFIG")
if not config_name:
    print("ERROR: FLASK_CONFIG environment variable not defined. Set to 'development' or 'testing' or 'production'")
    exit()

port = os.getenv("FLASK_PORT")
if not port:
    print("WARNING: FLASK_PORT environment variable not defined, using default port 5000")

if not os.getenv("MECHANIC_DEV_DATABASE") and config_name == "development":
    print("ERROR: No dev database url has been set. Set the MECHANIC_DEV_DATABASE environment variable.")
    exit()

if not os.getenv("MECHANIC_PRO_DATABASE") and config_name == "production":
    print("ERROR: No pro database url has been set. Set the MECHANIC_PRO_DATABASE environment variable.")
    exit()

if not os.getenv("MECHANIC_TEST_DATABASE") and config_name == "testing":
    print("ERROR: No test database url has been set. Set the MECHANIC_TEST_DATABASE environment variable.")
    exit()

app = create_app(config_name)

if __name__ == "__main__":
    if port:
        app.run(port=int(port))
    else:
        app.run()
