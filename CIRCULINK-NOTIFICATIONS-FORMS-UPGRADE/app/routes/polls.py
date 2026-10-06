from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, flash, abort
from app.db import get_db
from app.utils.ids import new
from app.utils.auth import user
from app.repositories.notifications import add
import re

polls_bp=Blueprint('polls',__name__,url_prefix='/polls')

def slugify(value):
    s=re.sub(r'[^a-z0-9]+','-',(value or '').lower()).strip('-')
    return s or 'poll'

@polls_bp.get('/<slug>')
def view(slug):
    db=get_db(); poll=db.polls.find_one({'slug':slug,'status':'active'}) if db is not None else None
    if not poll: abort(404)
    u=user()
    if poll.get('target_user_id') and (not u or u.get('_id') != poll['target_user_id']):
        return render_template('error.html', code=403, title='Private poll', message='This poll was shared with a specific CIRCULINK account.'),403
    return render_template('polls/view.html',poll=poll,voted=False)

@polls_bp.post('/<slug>/vote')
def vote(slug):
    db=get_db(); poll=db.polls.find_one({'slug':slug,'status':'active'}) if db is not None else None
    if not poll: abort(404)
    u=user()
    if poll.get('target_user_id') and (not u or u.get('_id') != poll['target_user_id']):
        return render_template('error.html', code=403, title='Private poll', message='This poll was shared with a specific CIRCULINK account.'),403
    option=request.form.get('option','')
    if option not in poll.get('options',[]): flash('Select one of the available choices.','error'); return redirect(f'/polls/{slug}')
    voter_id=u['_id'] if u else request.remote_addr
    if db.poll_votes.find_one({'poll_id':poll['_id'],'voter_id':voter_id}):
        flash('Your response has already been recorded.','info'); return redirect(f'/polls/{slug}')
    db.poll_votes.insert_one({'_id':new('vote_'),'poll_id':poll['_id'],'voter_id':voter_id,'option':option,'created_at':datetime.now(timezone.utc)})
    return render_template('polls/view.html',poll=poll,voted=True)
