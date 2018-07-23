import os
import json
import logging.config


levels = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL
}


def setup(default_path='logging.json', logfile=None, default_level=None, env_key='LOG_CFG'):
    """Setup logging configuration

       http://drtomstarke.com/index.php/adding-a-logger-to-your-applications/
       http://victorlin.me/posts/2012/08/26/good-logging-practice-in-python

       LOG_CFG: Environment config variable
       
       :param default_path: Path to the JSON file used to dictConf logging system
       :param logfile: file_handler filename attribute override
       :param default_level: level to use for basicConfig if no configuration is found or as an override
       :param env_key: if environment config variable with this name is set, then it will be used to configure filename
    """
    path = default_path
    # Check if the path is defined in the environment
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = json.load(f)
            # Override Log File location
            if logfile is not None:
                config['handlers']['file_handler']['filename'] = logfile
            # Override for all the handlers
            if default_level is not None:
                config['handlers']['console']['level'] = levels[default_level]
                config['handlers']['file_handler']['level'] = levels[default_level]
                config['root']['level'] = levels[default_level]
        logging.config.dictConfig(config)
    else:
        if default_level is None:
            default_level = 'info'
        logging.basicConfig(level=levels[default_level])
