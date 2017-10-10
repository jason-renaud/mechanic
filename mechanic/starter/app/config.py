import os


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
    SQLALCHEMY_DATABASE_URI = os.getenv("MECHANIC_DEV_DATABASE")
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY")


class ProductionConfig(Config):
    """
    Production configurations
    """

    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("MECHANIC_PRO_DATABASE")
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY")


class TestingConfig(Config):
    """
    Testing configurations
    """

    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv("MECHANIC_TEST_DATABASE")
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY")


app_config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig
}