from flask import Flask

def create_app():
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB
    app.config['UPLOAD_FOLDER'] = '/home/bradley/development/csreportcard/data/uploads'

    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app