import app
import argparse


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("conf")
    args = vars(parser.parse_args())

    app.init_app(args["conf"], app_type='DEV')
    app.app.run(debug=True)
