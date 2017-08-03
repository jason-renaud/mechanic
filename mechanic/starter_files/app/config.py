import configparser

parser = configparser.ConfigParser()
conf_file = "/etc/YOURAPPNAME_HERE/app.conf"
parser.read(conf_file)


class Config(object):
    """
    Common configurations
    """

    DEBUG = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class DevelopmentConfig(Config):
    """
    Development configurations
    """

    SQLALCHEMY_ECHO = True
    SQLALCHEMY_DATABASE_URI = parser.get("database", "dev")


class ProductionConfig(Config):
    """
    Production configurations
    """

    DEBUG = False
    SQLALCHEMY_DATABASE_URI = parser.get("database", "pro")


class TestingConfig(Config):
    """
    Testing configurations
    """

    TESTING = True
    SQLALCHEMY_DATABASE_URI = parser.get("database", "test")


app_config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig
}