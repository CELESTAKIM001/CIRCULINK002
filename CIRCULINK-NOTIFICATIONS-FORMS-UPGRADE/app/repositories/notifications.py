from datetime import datetime, timezone
from app.db import get_db
from app.utils.ids import new

def add(uid=None, title='', message='', kind='info', link_url='', audience='user'):
    db = get_db()
    if db is None:
        raise RuntimeError('Database is not configured.')
    doc = {'_id': new('not_'), 'user_id': uid, 'audience': audience, 'title': title.strip(), 'message': message.strip(), 'kind': kind, 'link_url': link_url.strip(), 'read': False, 'read_by': [], 'created_at': datetime.now(timezone.utc)}
    db.notifications.insert_one(doc)
    return doc

def for_user(uid, limit=60):
    db = get_db()
    if db is None or not uid:
        return []
    rows=list(db.notifications.find({'$or': [{'user_id': uid}, {'audience': 'all'}], 'status': {'$ne': 'inactive'}}).sort('created_at', -1).limit(limit))
    for row in rows:
        row['read'] = uid in row.get('read_by', []) if row.get('audience') == 'all' else bool(row.get('read'))
    return rows

def unread_count(uid):
    db = get_db()
    if db is None or not uid:
        return 0
    targeted=db.notifications.count_documents({'user_id':uid,'read':False,'status':{'$ne':'inactive'}})
    broadcast=db.notifications.count_documents({'audience':'all','status':{'$ne':'inactive'},'read_by':{'$ne':uid}})
    return targeted+broadcast

def mark_read(uid, notification_id=None):
    db = get_db()
    if db is None:
        return
    if notification_id:
        row=db.notifications.find_one({'_id':notification_id,'$or':[{'user_id':uid},{'audience':'all'}]})
        if not row: return
        if row.get('audience')=='all':
            db.notifications.update_one({'_id':notification_id},{'$addToSet':{'read_by':uid}})
        else:
            db.notifications.update_one({'_id':notification_id},{'$set':{'read':True,'read_at':datetime.now(timezone.utc)}})
        return
    db.notifications.update_many({'user_id':uid},{'$set':{'read':True,'read_at':datetime.now(timezone.utc)}})
    db.notifications.update_many({'audience':'all'},{'$addToSet':{'read_by':uid}})
