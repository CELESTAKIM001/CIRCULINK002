from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, flash, abort
from app.db import get_db
from app.utils.ids import new
from app.utils.auth import user
from app.repositories.notifications import add
from app.services.email import send
import re

forms_bp = Blueprint('forms', __name__, url_prefix='/forms')

def slugify(value):
    s = re.sub(r'[^a-z0-9]+', '-', (value or '').lower()).strip('-')
    return s or 'form'

def parse_fields(raw):
    fields=[]
    for line in (raw or '').splitlines():
        line=line.strip()
        if not line: continue
        parts=[x.strip() for x in line.split('|')]
        label=parts[0]
        kind=parts[1] if len(parts)>1 and parts[1] else 'text'
        required=(len(parts)>2 and parts[2].lower() in ('1','yes','true','required'))
        if kind not in ('text','email','number','date','textarea','select'): kind='text'
        fields.append({'name': re.sub(r'[^a-z0-9]+','_',label.lower()).strip('_') or f'field_{len(fields)+1}', 'label':label, 'type':kind, 'required':required})
    return fields

@forms_bp.get('/<slug>')
def view(slug):
    db=get_db(); form=db.forms.find_one({'slug':slug,'status':'active'}) if db is not None else None
    if not form: abort(404)
    u=user()
    if form.get('target_user_id') and (not u or u.get('_id') != form['target_user_id']):
        return render_template('error.html', code=403, title='Private form', message='This form was shared with a specific CIRCULINK account.'), 403
    return render_template('forms/view.html', form=form, submitted=False)

@forms_bp.post('/<slug>/submit')
def submit(slug):
    db=get_db(); form=db.forms.find_one({'slug':slug,'status':'active'}) if db is not None else None
    if not form: abort(404)
    u=user()
    if form.get('target_user_id') and (not u or u.get('_id') != form['target_user_id']):
        return render_template('error.html', code=403, title='Private form', message='This form was shared with a specific CIRCULINK account.'), 403
    answers={f['name']:request.form.get(f['name'],'').strip() for f in form.get('fields',[])}
    for f in form.get('fields',[]):
        if f.get('required') and not answers.get(f['name']):
            flash(f"{f['label']} is required.",'error'); return redirect(f"/forms/{slug}")
    db.form_submissions.insert_one({'_id':new('sub_'),'form_id':form['_id'],'slug':slug,'user_id':u['_id'] if u else None,'email':u.get('email') if u else request.form.get('email',''),'answers':answers,'created_at':datetime.now(timezone.utc)})
    return render_template('forms/view.html', form=form, submitted=True)
