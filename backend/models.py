import os 
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, DateTime
from dotenv import load_dotenv # Load environment variables
import datetime
from sqlalchemy import Column, Integer, String, DateTime, TIMESTAMP, text
from sqlalchemy.sql import text, func 
from sqlalchemy.schema import FetchedValue


db = SQLAlchemy()

database_name = os.getenv('DB_NAME')
database_path = "postgresql://{}:{}@{}/{}".format(os.getenv('DB_USER'), os.getenv('PASSWORD'), os.getenv('HOSTNAME'), database_name) # default 'localhost:5432'
# database_path = os.getenv('EXTERNAL_PATH_RENDER')

## Setup DB(app) bind the flask app with SQLAlchemy

def setup_db(app, database_path=database_path):
    app.config["SQLALCHEMY_DATABASE_URI"] = database_path
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
    db.app = app
    # db.drop_all() Elimina las tablas existentes en la bd cada vez que se llama a setup_db > Se comenta por error en unittest
    with app.app_context():
        db.create_all()

class Domains(db.Model):
    __tablename__ = 'domains'

    id = db.Column(db.Integer, primary_key=True)
    # name = db.Column(db.String, nullable=False, unique=True) # Domain name has to be unique
    domain = db.Column(db.String, nullable=False, unique=True) # Domain name has to be unique
    description = db.Column(db.String, nullable=False)
    is_verified = db.Column(db.Boolean, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False)
    create_date = db.Column(db.DateTime, default=datetime.datetime.utcnow(), nullable=False)

    def __init__(self, domain, description, is_verified, is_active, create_date):
        self.domain = domain
        self.description = description
        self.is_verified = is_verified
        self.is_active = is_active
        self.create_date = create_date
    
    def format(self):
        return {
            'id': self.id,
            'domain': self.domain,
            'description': self.description,
            'is_verified': self.is_verified,
            'is_active': self.is_active,
            'create_date': self.create_date
        }
    
    def insert(self):
        db.session.add(self)
        db.session.commit() 
    
    def update(self):
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()


class Phishing(db.Model):
    __tablename__ = 'phishing'

    id = db.Column(db.Integer, primary_key=True)
    domain_id = db.Column(db.Integer, db.ForeignKey('domains.id'), nullable=False)
    ip = db.Column(db.String, nullable=False)
    phishing_url = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=False)
    is_dangerous = db.Column(db.Boolean, nullable=False)
    submited_by = db.Column(db.String, nullable=False)
    create_date = db.Column(db.DateTime, default=datetime.datetime.utcnow(), nullable=False)
    
    def __init__(self, domain_id, ip, phishing_url, description, is_dangerous, submited_by, create_date):
        self.domain_id = domain_id
        self.ip = ip
        self.phishing_url = phishing_url
        self.description = description
        self.is_dangerous = is_dangerous
        self.submited_by = submited_by
        self.create_date = create_date
    
    def format(self):
        return {
            'id': self.id,
            'domain_id': self.domain_id,
            'ip': self.ip,
            'phishing_url': self.phishing_url,
            'description': self.description,
            'is_dangerous': self.is_dangerous,
            'submited_by': self.submited_by,
            'create_date': self.create_date
        }
    
    def insert(self):
        db.session.add(self)
        db.session.commit()
    
    def update(self):
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()

class Articles(db.Model):
    __tablename__ = 'articles'

    id = db.Column(db.Integer, primary_key=True)
    domain_id = db.Column(db.Integer, db.ForeignKey('domains.id'), nullable=False)
    title = db.Column(db.String, nullable=False)
    url = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=False)
    submited_by = db.Column(db.String, nullable=False)
    create_date = db.Column(db.DateTime, default=datetime.datetime.utcnow(), nullable=False)
    
    def __init__(self, domain_id, title, url, description, submited_by, create_date):
        self.domain_id = domain_id
        self.title = title
        self.url = url
        self.description = description
        self.submited_by = submited_by
        self.create_date = create_date

    def format(self):
        return {
            'id': self.id,
            'domain_id': self.domain_id,
            'title': self.title,
            'url': self.url,
            'description': self.description,
            'submited_by': self.submited_by,
            'create_date': self.create_date
        }

    def insert(self):
        db.session.add(self)
        db.session.commit()
    
    def update(self):
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()