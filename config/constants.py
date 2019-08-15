import os

# Auth
AUTH_EXPIRES_DAYS = 30
SESSION_KEY = os.environ.get('SESSION_KEY', b'replace with the output from base64.b64encode(os.urandom(64))')

# Database
DB_NAME = os.environ.get('DB_NAME', 'trestle')
DB_USER = os.environ.get('DB_USER', 'trestle_user')
DB_PASS = os.environ.get('DB_PASS', 'trestle_password')
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = os.environ.get('DB_PORT', '5432')

# SendGrid
# replace this with your own SendGrid API Key
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'replace.sender@yourdomain.com')
SUPPORT_EMAIL = os.environ.get('SUPPORT_EMAIL', 'replace.support@yourdomain.com')
