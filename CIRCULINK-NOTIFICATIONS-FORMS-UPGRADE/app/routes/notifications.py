from flask import Blueprint, render_template, redirect, request
from app.utils.auth import required, user
from app.repositories.notifications import for_user, mark_read

notifications_bp = Blueprint('notifications', __name__, url_prefix='/notifications')

@notifications_bp.get('/')
@required
def index():
    u = user()
    return render_template('notifications/index.html', notifications=for_user(u['_id'], 100), user=u)

@notifications_bp.post('/read/<notification_id>')
@required
def read(notification_id):
    u = user(); mark_read(u['_id'], notification_id)
    return redirect(request.form.get('next') or request.referrer or '/notifications/')

@notifications_bp.post('/read-all')
@required
def read_all():
    u = user(); mark_read(u['_id'])
    return redirect(request.form.get('next') or request.referrer or '/notifications/')
