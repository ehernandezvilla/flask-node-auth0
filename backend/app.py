import os
from dotenv import load_dotenv # Load enviroment variables
from flask import Flask, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from models import db, setup_db, Domains, Phishing, Articles
from flask import request
from datetime import datetime
from auth import AuthError, requires_auth
from sqlalchemy import event, exc
import psycopg2.extensions

# Carga las variables de entorno desde el archivo .env
load_dotenv()

database_name = os.getenv('DB_NAME')
database_path = "postgresql://{}:{}@{}/{}".format(os.getenv('DB_USER'), os.getenv('PASSWORD'), os.getenv('HOSTNAME'), database_name) # default 'localhost:5432'
# database_path = os.getenv('EXTERNAL_PATH_RENDER')

PHISHING_PER_PAGE = 10

def paginate_phishings(request, selection):
    page = request.args.get('page', 1, type=int)
    start = (page - 1) * PHISHING_PER_PAGE
    end = start + PHISHING_PER_PAGE

    phishings = [phishing.format() for phishing in selection]
    current_phishings = phishings[start:end]

    return current_phishings


# Function that create the app and return it
def create_app(test_config=None):
    # Create and configure the app 
    app = Flask(__name__)
    app.app_context().push()
    app.config["SQLALCHEMY_DATABASE_URI"] = database_path
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
    # Configuraciones adicionales del pool y manejo de desconexiones
    app.config["SQLALCHEMY_POOL_SIZE"] = 10
    app.config["SQLALCHEMY_POOL_TIMEOUT"] = 30
    app.config["SQLALCHEMY_POOL_RECYCLE"] = 1800
    CORS(app)

    # Inicializar extensiones 
    db.init_app(app)
    migrate = Migrate(app, db, render_as_batch=False) 

    with app.app_context():
        db.create_all()

    # Configurar el listener de ping

    # Configurar el listener de ping
    def ping_listener(dbapi_connection, connection_record, connection_proxy):
        if isinstance(dbapi_connection, psycopg2.extensions.connection):
            try:
                # Ejecutar una consulta simple para verificar la conexión
                with dbapi_connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()

            except psycopg2.Error as err:
                if err.pgcode in ['57P01', '08006', '08003']:
                    # Reconectar si la conexión se ha perdido o se ha cerrado
                    connection_proxy._pool.dispose()
                    raise exc.DisconnectionError()

        else:
            connection_proxy._pool.dispose()
            raise exc.DisconnectionError()

    # Create the routes

    # Home route 
    @app.route('/')
    def index():
        return 'Hey! Welcome to the FSND home project!' 
        
    # Domain routes 
    @app.route('/domains') # GET - Domains
    def get_domains():
        domains = Domains.query.all()
        current_domains = paginate_phishings(request, domains)

        if len(current_domains) == 0:
            abort(404)

        return jsonify(
            {
                "success": True,
                "domains": current_domains,
                "total_domains": len(Domains.query.all())
                }
            )


    @app.route('/domains/<int:id>') # GET - Domain id
    @requires_auth('get:domains') # User
    def get_domain(jwt,id):
    
        try:
            domain = Domains.query.get(id)
            return jsonify(domain.format())
        except:
            abort(404)
    
    @app.route('/domains', methods=['POST']) # POST - Domain
    @requires_auth('post:domains') # Admin
    def add_domain(jwt):
        data = request.get_json()

        domain = Domains(
            domain = data['domain'],
            description = data['description'],
            is_active = data['is_active'],
            is_verified = data['is_verified'],
            create_date = datetime.strptime(data['create_date'], '%d-%m-%Y') # Adjusted for day-month-year format
        )
        db.session.add(domain)
        db.session.commit()
        
        return jsonify({
        'message': 'New domain added',
        'domain': {
            'id': domain.id,
            'domain': domain.domain,
            'description': domain.description,
            'is_active': domain.is_active,
            'is_verified': domain.is_verified,
            'create_date': domain.create_date.strftime('%Y-%m-%d %H:%M:%S') # Return date as string in this format
        }
    }), 201


    @app.route('/domains/<int:id>', methods=['PATCH']) # PATCH - Domain
    @requires_auth('patch:domains') # Admin
    def update_domain(jwt, id):
        data = request.get_json()
        domain = Domains.query.get(id)
        domain.domain = data['domain']
        domain.description = data['description']
        domain.is_active = data['is_active']
        domain.is_verified = data['is_verified']
        domain.create_date = datetime.strptime(data['create_date'], '%d-%m-%Y') # Adjusted for day-month-year format
        db.session.commit()
        
        return jsonify({
            'message': 'Domain updated',
            'domain': {
                'id': domain.id,
                'domain': domain.domain,
                'description': domain.description,
                'is_active': domain.is_active,
                'is_verified': domain.is_verified,
                'create_date': domain.create_date.strftime('%Y-%m-%d %H:%M:%S') # Return date as string in this format
            }
        }), 200
    
    @app.route('/domains/<int:id>', methods=['DELETE']) # DELETE - Domain
    @requires_auth('delete:domains') # Admin
    def delete_domain(jwt, id):
        domain = Domains.query.get(id)
        db.session.delete(domain)
        db.session.commit()
        
        return jsonify({
            'message': 'Domain deleted'
        }), 200


    # Phishing routes

    @app.route('/phishing') # GET - Phishing
    def get_phishing():
        selection = Phishing.query.order_by(Phishing.id).all()
        current_phishings = paginate_phishings(request, selection)

        if len(current_phishings) == 0:
            abort(404)
        
        return jsonify({
            "success": True,
            "phishings": current_phishings,
            "total_phishings": len(selection)
            })

    @app.route('/phishing/<int:id>') # GET - Phishing id
    @requires_auth('get:phishing') # User
    def get_phishing_by_id(jwt, id):
        try:
                
            phishing = Phishing.query.get(id)
            return jsonify(phishing.format())

        except:
            abort(404)

    @app.route('/phishing/count')  # GET - Phishing count
    @requires_auth('get:phishing') # User
    def get_phishing_count(jwt):
        count = Phishing.query.count()
        return jsonify({'count': count})
    
    @app.route('/phishing/search', methods=['GET','POST']) # POST - Phishing search
    def search_phishing():
        search_data = request.get_json()
        search_term = search_data.get('search_term')
        search = f"%{search_term}%"

        data = Phishing.query.filter(Phishing.phishing_url.ilike(search)).all()

        items = []
        for row in data:
            aux = {
                "id": row.id,
                "create_date": row.create_date,
                "description": row.description,
                "is_dangerous": row.is_dangerous,
                "ip": row.ip,
                "phishing_url": row.phishing_url,
                "submited_by": row.submited_by
            }
            items.append(aux)

        response = {
            "count": len(items),
            "data": items
        }

        return jsonify(response)

    @app.route('/phishing', methods=['POST']) # POST - Phishing
    @requires_auth('post:phishing') # Admin
    def add_phishing(jwt):
        data = request.get_json()
        phishing = Phishing(
            domain_id = data['domain_id'],
            description = data['description'],
            ip = data['ip'],
            is_dangerous = data['is_dangerous'],
            phishing_url = data['phishing_url'],
            submited_by = data['submited_by'],
            create_date = datetime.strptime(data['create_date'], '%d-%m-%Y') # Adjusted for day-month-year format
        )
        db.session.add(phishing)
        db.session.commit()
        
        return jsonify({
        'message': 'New phishing domain added',
        'phishing': {
            'id': phishing.id,
            'domain_id': phishing.domain_id,
            'description': phishing.description,
            'ip': phishing.ip,
            'is_dangerous': phishing.is_dangerous,
            'phishing_url': phishing.phishing_url,
            'submited_by': phishing.submited_by,
            'create_date': phishing.create_date.strftime('%Y-%m-%d %H:%M:%S') # Return date as string in this format
                }
        }), 201 
    
    @app.route('/phishing/<int:id>', methods=['PATCH']) # PATCH - Phishing
    @requires_auth('patch:phishing') # Admin
    def update_phishing(jwt,id):
        data = request.get_json()
        phishing = Phishing.query.get(id)
        phishing.domain_id = data['domain_id']
        phishing.description = data['description']
        phishing.ip = data['ip']
        phishing.is_dangerous = data['is_dangerous']
        phishing.phishing_url = data['phishing_url']
        phishing.submited_by = data['submited_by']
        phishing.create_date = datetime.strptime(data['create_date'], '%d-%m-%Y') # Adjusted for day-month-year format
        db.session.commit()
        
        return jsonify({
            'message': 'Phishing domain updated',
            'phishing': {
                'id': phishing.id,
                'domain_id': phishing.domain_id,
                'description': phishing.description,
                'ip': phishing.ip,
                'is_dangerous': phishing.is_dangerous,
                'phishing_url': phishing.phishing_url,
                'create_date': phishing.create_date.strftime('%Y-%m-%d %H:%M:%S') # Return date as string in this format
                }
            }), 200
    
    @app.route('/phishing/<int:id>', methods=['DELETE']) # DELETE - Phishing
    @requires_auth('delete:phishing') # Admin
    def delete_phishing(jwt,id):
        phishing = Phishing.query.get(id)
        db.session.delete(phishing)
        db.session.commit()
        
        return jsonify({
            'message': 'Phishing domain deleted'
        }), 200

    # Articles routes
    @app.route('/articles') # GET - Articles
    def get_articles():
        try:
            articles = Articles.query.all()
            if not articles:
                abort(404)  # Si no se encuentran artículos, devolver error 404

            return jsonify([article.format() for article in articles])
        except:
            abort(500)  # Si hay algún otro error, devolver error 500
    
    @app.route('/articles/<int:id>') # GET - Articles id
    @requires_auth('get:articles') # User
    def get_articles_by_id(jwt,id):
        try:
            articles = Articles.query.get(id)
            return jsonify(articles.format())
        except:
            abort(404)
    
    @app.route('/articles', methods=['POST']) # POST - Articles
    @requires_auth('post:articles') # Admin
    def add_articles(jwt):
        data = request.get_json()
        articles = Articles(
            title = data['title'],
            description = data['description'],
            url = data['url'],
            submited_by = data['submited_by'],
            domain_id = data['domain_id'],
            create_date = datetime.strptime(data['create_date'], '%d-%m-%Y') # Adjusted for day-month-year format
        )
        db.session.add(articles)
        db.session.commit()
        
        return jsonify({
        'message': 'New article added',
        'article': {
            'id': articles.id,
            'domain_id': articles.domain_id,
            'title': articles.title,
            'description': articles.description,
            'url': articles.url,
            'submited_by': articles.submited_by,
            'create_date': articles.create_date.strftime('%Y-%m-%d %H:%M:%S') # Return date as string in this format
            }
        }), 201

    @app.route('/articles/<int:id>', methods=['PATCH']) # PATCH - Articles
    @requires_auth('patch:articles') # Admin
    def update_articles(jwt,id):
        data = request.get_json()
        articles = Articles.query.get(id)
        articles.title = data['title']
        articles.description = data['description']
        articles.url = data['url']
        articles.submited_by = data['submited_by']
        articles.domain_id = data['domain_id']
        articles.create_date = datetime.strptime(data['create_date'], '%d-%m-%Y') # Adjusted for day-month-year format
        db.session.commit()
        
        return jsonify({
            'message': 'Article updated',
            'article': {
                'id': articles.id,
                'domain_id': articles.domain_id,
                'title': articles.title,
                'description': articles.description,
                'url': articles.url,
                'submited_by': articles.submited_by,
                'create_date': articles.create_date.strftime('%Y-%m-%d %H:%M:%S') # Return date as string in this format
                }
            }), 200
    
    @app.route('/articles/<int:id>', methods=['DELETE']) # DELETE - Articles
    @requires_auth('delete:articles') # Admin
    def delete_articles(jwt,id):
        articles = Articles.query.get(id)
        db.session.delete(articles)
        db.session.commit()
        
        return jsonify({
            'message': 'Article deleted'
        }), 200


    # Error handlers

    @app.errorhandler(404) # Error handler for 404 not found
    def error404(error):
        return jsonify({
            'success': False,
            'error': 404,
            'message': 'Not found'
        }), 404
    
    @app.errorhandler(401) # Error handler for 401 unauthorized
    def error401(error):
        return jsonify({
            'success': False,
            'error': 401,
            'message': 'Unauthorized'
        }), 401
    
    @app.errorhandler(405) # Error handler for 405 method not allowed
    def error405(error):
        return jsonify({
            'success': False,
            'error': 405,
            'message': 'Method not allowed'
            }), 405
    
    @app.errorhandler(422) # Error handler for 422 unprocessable entity
    def error422(error):
        return jsonify({
            'success': False,
            'error': 422,
            'message': 'Unprocessable entity'
            }), 422
    
    @app.errorhandler(400) # Error handler for 400 bad request
    def error400(error):
        return jsonify({
            'success': False,
            'error': 400,
            'message': 'Bad request'
            }), 400


#### Section change ####

# Return the already created app 
    return app 

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
