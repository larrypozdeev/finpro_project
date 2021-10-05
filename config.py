import json
import pkgutil
import logging
import logging.config


logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "": {
                "format": "[%(asctime)s] %(levelname)-8s | %(name)-25s | %(message)s",
            },
            "consoleFormatter": {
                "format": "%(levelname)-8s | %(name)-10s | %(message)s",
            },
            "fileFormatter": {
                "format": "[%(asctime)s] %(levelname)-8s | %(name)-25s | %(message)s",
            },
        },
        "handlers": {
            # "file": {
            #     "filename": "tmp/debug.log",
            #     "level": "DEBUG",
            #     "class": "logging.FileHandler",
            #     "formatter": "fileFormatter",
            # },
            "console": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "consoleFormatter",
            },
        },
        "loggers": {
            "": {
                "handlers": ["console"],
                "level": "DEBUG",
            },
            "main": {
                "handlers": ["console"],
                "level": "DEBUG",
            },
            "file_handler": {
                "handlers": ["console"],
                "level": "DEBUG",
            },
        },
    }
)

help_bin = pkgutil.get_data("config", "creds.json")
creds_json = help_bin.decode("UTF-8", "ignore")
creds_json = json.loads(creds_json)
DEBUG = True


def log_fun(fn):
    from functools import wraps

    @wraps(fn)
    def wrapper(*args, **kwargs):
        log = logging.getLogger(fn.__name__)
        log.info("About to run %s" % fn.__name__)

        out = fn(*args, **kwargs)

        log.info("Done running %s" % fn.__name__)

        return out

    return wrapper


if DEBUG:
    help_bin = pkgutil.get_data("config", "settings_dev.json")
    settings_data = help_bin.decode("UTF-8", "ignore")
    settings_data = json.loads(settings_data)
else:
    help_bin = pkgutil.get_data("config", "settings.json")
    settings_data = help_bin.decode("UTF-8", "ignore")
    settings_data = json.loads(settings_data)
