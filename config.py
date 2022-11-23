import json


def load_config():
    r"""Loads the config from ".\config.json"

    Returns:
        dict: config as Python dictionary
    """
    with open("config.json", "r") as file:
        config = json.load(file)

    return config
