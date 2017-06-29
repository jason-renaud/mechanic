import shutil
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dir")
    parser.add_argument("--base-only", action="store_true")
    parser.add_argument("--app-only", action="store_true")
    parser.add_argument("--tests-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = vars(parser.parse_args())

    if args["force"]:
        shutil.rmtree(args["dir"] + "/base/")
        shutil.rmtree(args["dir"] + "/app/")
        shutil.rmtree(args["dir"] + "/tests/")

    if args["base_only"]:
        shutil.rmtree(args["dir"] + "/base/", ignore_errors=True)
        shutil.copytree("starter_files/base/", args["dir"] + "/base/")
        exit()

    if args["app_only"]:
        shutil.rmtree(args["dir"] + "/app/", ignore_errors=True)
        shutil.copytree("starter_files/app/", args["dir"] + "/app/")
        exit()

    if args["tests_only"]:
        shutil.rmtree(args["dir"] + "/tests/", ignore_errors=True)
        shutil.copytree("starter_files/tests/", args["dir"] + "/tests/")
        exit()

    shutil.copytree("starter_files/base/", args["dir"] + "/base/")
    shutil.copytree("starter_files/app/", args["dir"] + "/app/")
    shutil.copytree("starter_files/tests/", args["dir"] + "/tests/")
    shutil.copy("starter_files/requirements.txt", args["dir"])
    shutil.copy("starter_files/run.py", args["dir"])