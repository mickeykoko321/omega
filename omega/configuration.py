import os
import sys
import yaml

import omega.logger.init_logger as il

"""Configuration module

This module is used to load the configuration as defined in the config file.
"""
cfg = []


def initialization(filename=None):
    """Read and return configuration file. Must have the name omega.config!!!"""
    global cfg

    # Configuration
    root = os.path.abspath(os.path.dirname(__file__))
    try:
        with open(os.path.join(root, 'omega.config'), 'r') as y_cfg:
            cfg = yaml.load(y_cfg)
    except FileNotFoundError:
        print('Configuration file not found!')
        sys.exit(1)
    # Initialize logger
    # TODO: Eventually find a better way to do this (see also in run: call to init)!
    filename = 'run-logs.txt' if filename is None else filename
    log_config = os.path.join(cfg['default']['root'], 'logger', 'logging.json')
    log_file = os.path.join(cfg['logging']['root'], filename)
    il.setup(default_path=log_config, logfile=log_file, default_level=cfg['logging']['level'])


# Read configuration
initialization()
