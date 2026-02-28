"""Google OAuth authentication using authlib"""
import os
from flask import Blueprint, redirect, url_for, flash
from flask_login import login_user, logout_user
from authlib.integrations.flask_client import OAuth
from models import db, User, SocialAuth 

auth_bp = Blueprint('auth', __name__)
oauth = OAuth()

def init_oauth(app):
    """Initialize OAuth with Flask app"""
    oauth.init_app(app)
    oauth.register(
        name='google',
        client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )

@auth_bp.route('/login')
def login():
    """Initiate Google OAuth login"""
    redirect_uri = url_for('auth.callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth_bp.route('/auth/callback')
def callback():
    """Handle Google OAuth callback"""
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')

        if not user_info:
            flash('Failed to get user info from Google', 'error')
            return redirect(url_for('auth.login'))

                # Find or create user via SocialAuth
        social_auth = SocialAuth.query.filter_by(
            provider='google',
            provider_user_id=user_info['sub']
        ).first()

        if social_auth:
            # Existing user - log them in
            user = social_auth.user
            flash(f'Welcome back, {user.first_name}!', 'success')
        else:
            # New user - create account and link Google
            user = User(
                email=user_info['email'],
                first_name=user_info.get('given_name', user_info.get('name', 'User')),
                last_name=user_info.get('family_name')
            )
            db.session.add(user)
            db.session.flush()  # Get user.id without committing yet
            
            # Link Google account
            social_auth = SocialAuth(
                user_id=user.id,
                provider='google',
                provider_user_id=user_info['sub']
            )
            db.session.add(social_auth)
            db.session.commit()

            # Seed default categories for new user
            from seed_data import seed_user_categories
            seed_user_categories(user.id)

            flash(f'Welcome {user.first_name}! Your account has been created.', 'success')

        login_user(user)
        return redirect(url_for('home'))

    except Exception as e:
        flash(f'Authentication failed: {str(e)}', 'error')
        return redirect(url_for('auth.login'))


@auth_bp.route('/logout')
def logout():
    """Logout current user"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('landing'))
