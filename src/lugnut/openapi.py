import json

from lugnut.app import create_app

if __name__ == "__main__":
    print(json.dumps(create_app().openapi()))
