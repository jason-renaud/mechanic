import shutil
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dir")
    args = vars(parser.parse_args())

    shutil.copytree("starter_files/base/", args["dir"] + "/base/")
    shutil.copytree("starter_files/app/", args["dir"] + "/app/")
    shutil.copytree("starter_files/tests/", args["dir"] + "/tests/")
    shutil.copy("starter_files/requirements.txt", args["dir"])
    shutil.copy("starter_files/run.py", args["dir"])