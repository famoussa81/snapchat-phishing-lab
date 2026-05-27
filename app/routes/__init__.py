from .auth import auth_bp
from .api import api_bp
from .campaign import campaign_bp
from .admin import admin_bp, require_admin

blueprints = [auth_bp, api_bp, campaign_bp, admin_bp]
