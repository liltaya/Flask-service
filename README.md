Flask Service

REST API built with Flask, PostgreSQL, SQLAlchemy, Nginx, systemd, and Prometheus metrics.

Features
CRUD REST endpoints
PostgreSQL persistence
JSON input validation
Health endpoint
Prometheus metrics
Nginx reverse proxy
systemd service
Automated Bash deployment
HTTP and database error handling
API endpoints
Method	Endpoint	Description
GET	/	API information
GET	/health	Application and database health
GET	/metrics	Prometheus metrics
GET	/items	List all items
GET	/items/<id>	Get an item
POST	/items	Create an item
PUT	/items/<id>	Update an item
DELETE	/items/<id>	Delete an item
Requirements
Ubuntu Linux
PostgreSQL
Python 3
Nginx
systemd
Git

The deployment script installs the required operating-system packages and Python dependencies.

Environment configuration

Create /opt/flask-service/.env:

DATABASE_URL=postgresql+psycopg://flask_service_user:password@127.0.0.1:5432/flask_service

Protect the file:

sudo chown flaskapp:flaskapp /opt/flask-service/.env
sudo chmod 600 /opt/flask-service/.env

Do not commit .env to Git.

Automated deployment

Clone the repository:

git clone https://github.com/liltaya/Flask-service.git
cd Flask-service

Create the application user and directory:

sudo useradd \
  --system \
  --create-home \
  --shell /usr/sbin/nologin \
  flaskapp

sudo mkdir -p /opt/flask-service

Copy the project:

sudo rsync -a \
  --exclude='.git' \
  ./ \
  /opt/flask-service/

sudo chown -R flaskapp:flaskapp /opt/flask-service

Run deployment:

cd /opt/flask-service
sudo chmod +x deploy.sh
sudo ./deploy.sh

The deployment script performs the following operations:

Installs operating-system dependencies.
Creates the Python virtual environment.
Installs packages from requirements.txt.
Copies application and deployment configuration files.
Installs the systemd service.
Installs and validates the Nginx configuration.
Restarts the Flask and Nginx services.
Checks the /health endpoint.
Prints service diagnostics if deployment fails.
Verification

Check service status:

sudo systemctl is-active flask-service
sudo systemctl is-active nginx
sudo systemctl is-active postgresql

Test the health endpoint through Nginx:

curl -i http://127.0.0.1/health

Expected response:

{
  "status": "ok",
  "database": "connected"
}
CRUD examples

Create an item:

curl -i -X POST http://127.0.0.1/items \
  -H "Content-Type: application/json" \
  -d '{"name":"Demo item"}'

Get all items:

curl -i http://127.0.0.1/items

Update an item:

curl -i -X PUT http://127.0.0.1/items/1 \
  -H "Content-Type: application/json" \
  -d '{"name":"Updated item"}'

Delete an item:

curl -i -X DELETE http://127.0.0.1/items/1
Input validation

The API validates:

Content-Type: application/json
valid JSON syntax
JSON object structure
presence of the name field
string type
non-empty values
maximum length of 200 characters
Error handling

The application returns JSON errors for:

400 Bad Request
404 Not Found
405 Method Not Allowed
415 Unsupported Media Type
500 Internal Server Error
503 Service Unavailable

Nginx returns 502 Bad Gateway when the Flask upstream is unavailable.

Logs

Application service logs:

sudo journalctl -u flask-service -n 100 --no-pager

Nginx error logs:

sudo tail -n 100 /var/log/nginx/error.log
Security
Database credentials are stored in .env.
.env is excluded through .gitignore.
Flask listens behind Nginx.
Debug mode is disabled.
The application runs as the unprivileged flaskapp user.
Port 5000 should not be exposed publicly.
