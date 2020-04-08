import os

# load environment variables from a file if it exists - the ENV var is set by supervisor
env = os.environ.get('ENV')
if env:
    config_dir = os.path.dirname(os.path.realpath(__file__))
    env_file = os.path.join(config_dir, '.' + env)
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f.read().splitlines():
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

# Auth
AUTH_EXPIRES_DAYS = 30
SESSION_KEY = os.environ.get('SESSION_KEY', b'replace with the output from base64.b64encode(os.urandom(64))')
HOST = os.environ.get('HOST', 'localhost')

# Database
DB_NAME = os.environ.get('DB_NAME', 'trestle')
DB_USER = os.environ.get('DB_USER', 'trestle_user')
DB_PASS = os.environ.get('DB_PASS', 'trestle_password')
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_SSLMODE = os.environ.get('DB_SSLMODE', 'allow')

# SendGrid
# replace this with your own SendGrid API Key
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'replace.sender@yourdomain.com')
SUPPORT_EMAIL = os.environ.get('SUPPORT_EMAIL', 'replace.support@yourdomain.com')
