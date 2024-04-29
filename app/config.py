import os

class Config:
    #SECRET_KEY = os.environ.get('SECRET_KEY', 'default_secret_key')
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'data', 'uploads')
    OUTPUT_FOLDER = os.path.join(BASE_DIR, 'data', 'output')
    REPORT_CARDS_FOLDER = os.path.join(OUTPUT_FOLDER, 'data', 'report_cards')
    INDIVIDUAL_FOLDER = os.path.join(REPORT_CARDS_FOLDER, 'individual')
    TEMPLATE_FOLDER = os.path.join(BASE_DIR, 'app', 'report_generation', 'templates', 'pdf')
    RIBBONS_CSV = os.path.join(BASE_DIR, 'data', 'mapping', 'ribbons.csv')
    SKILL_NAMES_CSV = os.path.join(BASE_DIR, 'data', 'mapping', 'skill_names.csv')

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    #SECRET_KEY = os.environ.get('SECRET_KEY')
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', Config.UPLOAD_FOLDER)
    OUTPUT_FOLDER = os.environ.get('OUTPUT_FOLDER', Config.OUTPUT_FOLDER)
    INDIVIDUAL_FOLDER = os.environ.get('INDIVIDUAL_FOLDER', Config.INDIVIDUAL_FOLDER)
    REPORT_CARDS_FOLDER = os.environ.get('REPORT_CARDS_FOLDER', Config.REPORT_CARDS_FOLDER)
    TEMPLATE_FOLDER = os.environ.get('TEMPLATE_FOLDER', Config.TEMPLATE_FOLDER)
    RIBBONS_CSV = os.environ.get('RIBBONS_CSV', Config.RIBBONS_CSV)
    SKILL_NAMES_CSV = os.environ.get('SKILL_NAMES_CSV', Config.SKILL_NAMES_CSV)

class TestingConfig(Config):
    TESTING = True
    # You can define different paths for testing if required
