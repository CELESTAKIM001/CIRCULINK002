from datetime import datetime, timezone
from flask import Blueprint, render_template, request, flash, redirect
from app.utils.auth import admin
from app.db import get_db
from app.services.analytics import stats
from app.utils.ids import new

admin_bp=Blueprint("admin",__name__,url_prefix="/admin")
def now(): return datetime.now(timezone.utc)
def _collection(name,limit=200,projection=None):
    db=get_db()
    return [] if db is None else list(db[name].find({},projection or {}).sort("created_at",-1).limit(limit))
def _audit(action, target="", detail=""):
    db=get_db()
    if db is not None: db.audit_logs.insert_one({"_id":new("aud_"),"action":action,"target":target,"detail":detail,"actor_id":"ADMIN","created_at":now()})

def _flow_data():
    db=get_db()
    if db is None: return {"companies":0,"sources":0,"individuals":0,"requests":0,"fulfillments":0,"links":[]}
    companies=db.users.count_documents({"account_type":"company"}); sources=db.users.count_documents({"account_type":"source"}); individuals=db.users.count_documents({"account_type":"individual"})
    links=[]
    for f in db.fulfillments.find({}, {"company_id":1,"source_id":1,"individual_id":1,"company_name":1,"source_name":1,"individual_name":1,"status":1}).sort("created_at",-1).limit(80):
        links.append({"company":f.get("company_name") or f.get("company_id","Company"),"source":f.get("source_name") or f.get("source_id","Source"),"individual":f.get("individual_name") or f.get("individual_id","Individual"),"status":f.get("status","PENDING")})
    return {"companies":companies,"sources":sources,"individuals":individuals,"requests":db.material_requests.count_documents({}),"fulfillments":db.fulfillments.count_documents({}),"links":links}

@admin_bp.get("/")
@admin
def dashboard():
    db=get_db(); logs=[] if db is None else list(db.audit_logs.find().sort("created_at",-1).limit(20))
    return render_template("admin/dashboard.html",stats=stats(),logs=logs,flow=_flow_data())

@admin_bp.post("/action")
@admin
def action():
    db=get_db()
    if db is None: flash("Database is not connected.","error"); return redirect(request.referrer or "/admin/")
    collection=request.form.get("collection",""); item_id=request.form.get("id",""); action=request.form.get("action","").upper()
    allowed={"users","listings","plans","notifications","material_requests","fulfillments","payouts","point_redemptions","certificates","contact_messages","forms","polls"}
    if collection not in allowed or not item_id: flash("Invalid administrative action.","error"); return redirect(request.referrer or "/admin/")
    col=db[collection]
    status_map={"ACTIVATE":"active","DEACTIVATE":"inactive","APPROVE":"APPROVED","REJECT":"REJECTED","RESOLVE":"RESOLVED","READ":"READ","ARCHIVE":"ARCHIVED","QUEUE":"QUEUED","PAID":"PAID","REVOKE":"REVOKED","VERIFY":"VERIFIED"}
    if action=="DELETE": col.delete_one({"_id":item_id}); _audit("DELETE",f"{collection}:{item_id}")
    elif action in status_map: col.update_one({"_id":item_id},{"$set":{"status":status_map[action],"updated_at":now()}}); _audit(action,f"{collection}:{item_id}")
    elif action=="TOGGLE_VERIFIED":
        x=col.find_one({"_id":item_id}); col.update_one({"_id":item_id},{"$set":{"verified":not bool(x.get("verified")) if x else False,"updated_at":now()}}); _audit("TOGGLE_VERIFIED",f"{collection}:{item_id}")
    elif action=="ADMIN_BADGE":
        u=col.find_one({"_id":item_id})
        if u: db.badges.insert_one({"_id":new("bdg_"),"user_id":item_id,"name":request.form.get("badge_name","Verified Circular Participant"),"reason":request.form.get("reason","Admin recognition"),"issued_by":"ADMIN","created_at":now()}); _audit("BADGE_ISSUED",item_id)
    elif action=="REPLY":
        from app.services.email import send
        m=col.find_one({"_id":item_id})
        if m:
            ok=send(m.get("email"),request.form.get("subject","CIRCULINK response"),f"<h2>CIRCULINK response</h2><p>{request.form.get('message','')}</p>")
            col.update_one({"_id":item_id},{"$set":{"reply":request.form.get("message",""),"reply_sent":bool(ok),"status":"RESOLVED" if ok else "READ","updated_at":now()}})
    else: flash("Action not supported.","error"); return redirect(request.referrer or "/admin/")
    flash(f"{action.replace('_',' ').title()} completed.","success"); return redirect(request.referrer or "/admin/")

@admin_bp.post("/users/create")
@admin
def user_create():
    db=get_db()
    if db is None: flash("Database is not connected.","error"); return redirect("/admin/users")
    from werkzeug.security import generate_password_hash
    import bcrypt
    email=request.form.get("email","").lower().strip()
    if not email or db.users.find_one({"email":email}): flash("That email already exists or is invalid.","error"); return redirect("/admin/users")
    password=request.form.get("password","")
    if len(password)<6: flash("Password must be at least 6 characters.","error"); return redirect("/admin/users")
    doc={"_id":new("usr_"),"name":request.form.get("name","").strip(),"email":email,"phone":request.form.get("phone","").strip(),"password_hash":bcrypt.hashpw(password.encode(),bcrypt.gensalt()).decode(),"role":request.form.get("role","USER"),"account_type":request.form.get("account_type","individual"),"verified":bool(request.form.get("verified")),"status":"active","points_balance":0,"lifetime_points":0,"created_at":now()}
    db.users.insert_one(doc); _audit("USER_CREATED",doc["_id"]); flash("Account created.","success"); return redirect("/admin/users")

@admin_bp.get("/users")
@admin
def users(): return render_template("admin/users.html",users=_collection("users",300,{"password_hash":0}))

@admin_bp.get("/listings")
@admin
def listings(): return render_template("admin/listings.html",listings=_collection("listings",300))

@admin_bp.get("/payments")
@admin
def payments(): return render_template("admin/payments.html",payments=_collection("transactions",300))

@admin_bp.route("/plans",methods=["GET","POST"])
@admin
def plans():
    db=get_db()
    if db is None: return render_template("admin/plans.html",plans=[]),503
    if not db.plans.find_one():
        db.plans.insert_many([{"name":"Individual Free","price":0,"audience":"individual","active":True,"features":["Basic participation","Points wallet"]},{"name":"Source Standard","price":1500,"audience":"source","active":True,"features":["Source profile","Collection records"]},{"name":"Company Compliance","price":5000,"audience":"company","active":True,"features":["Material requests","Compliance records","Certificates"]}])
    if request.method=="POST":
        name=request.form.get("name","").strip(); features=[x.strip() for x in request.form.get("features","").splitlines() if x.strip()]
        db.plans.update_one({"name":name},{"$set":{"price":float(request.form.get("price",0) or 0),"active":bool(request.form.get("active")),"audience":request.form.get("audience","individual"),"features":features,"updated_at":now()}},upsert=True); _audit("PLAN_SAVED",name); flash("Plan saved.","success")
    return render_template("admin/plans.html",plans=list(db.plans.find().sort("price",1)))

@admin_bp.route("/settings",methods=["GET","POST"])
@admin
def settings():
    db=get_db()
    if db is None: return render_template("admin/settings.html",pricing={}),503
    current=db.settings.find_one({"key":"pricing"}) or {"value":{}}
    pricing={"tax_enabled":True,"tax_percent":0.0,"service_fee_percent":0.0,"pickup_fee":0.0,**current.get("value",{})}
    if request.method=="POST":
        pricing={"tax_enabled":bool(request.form.get("tax_enabled")),"tax_percent":max(0,float(request.form.get("tax_percent",0))),"service_fee_percent":max(0,float(request.form.get("service_fee_percent",0))),"pickup_fee":max(0,float(request.form.get("pickup_fee",0))),"currency":"KES"}; db.settings.update_one({"key":"pricing"},{"$set":{"value":pricing,"updated_at":now()}},upsert=True); flash("Finance settings updated.","success")
    return render_template("admin/settings.html",pricing=pricing)

@admin_bp.route("/mhub",methods=["GET","POST"])
@admin
def mhub():
    db=get_db(); current=(db.settings.find_one({"key":"mhub_ad"}) or {}).get("value",{})
    default={"enabled":True,"kicker":"M-HUB 2026 · NYERI","title":"Built during the M-Hub 2026 innovation season","text":"CIRCULINK was developed by GEOPRAM TECHNOLOGIES and friends at Nyeri.","link_url":"/about","link_label":"About the build"}; default.update(current)
    if request.method=="POST":
        value={"enabled":bool(request.form.get("enabled")),"kicker":request.form.get("kicker","M-HUB 2026 · NYERI").strip(),"title":request.form.get("title","").strip(),"text":request.form.get("text","").strip(),"link_url":request.form.get("link_url","/about").strip(),"link_label":request.form.get("link_label","Learn more").strip()}; db.settings.update_one({"key":"mhub_ad"},{"$set":{"value":value,"updated_at":now()}},upsert=True); _audit("MHUB_AD_UPDATED"); flash("M-Hub feature banner updated.","success"); default=value
    return render_template("admin/mhub.html",ad=default)

@admin_bp.get("/notifications")
@admin
def notifications():
    db=get_db(); users=_collection("users",300,{"password_hash":0})
    return render_template("admin/notifications.html",notifications=_collection("notifications"),users=users)

@admin_bp.post("/notifications/create")
@admin
def notification_create():
    db=get_db()
    if db is not None:
        from app.repositories.notifications import add
        audience=request.form.get("audience","all")
        target=request.form.get("user_id","").strip() or None
        doc=add(target,request.form.get("title",""),request.form.get("message",""),request.form.get("kind","info"),request.form.get("link_url",""),audience if audience in ("all","user") else "all")
        if target:
            recipient=db.users.find_one({"_id":target})
            if recipient and recipient.get("email") and request.form.get("send_email"):
                from app.services.email import send
                send(recipient["email"],request.form.get("title","CIRCULINK update"),f"<h2>{request.form.get('title','CIRCULINK update')}</h2><p>{request.form.get('message','')}</p><p><a href=\"{request.form.get('link_url','/')}\">Open in CIRCULINK</a></p>")
        _audit("NOTIFICATION_CREATED",doc["_id"],f"audience={audience};target={target or 'all'}")
        flash("Notification created and made available in the website notification center.","success")
    return redirect("/admin/notifications")


@admin_bp.route("/forms", methods=["GET","POST"])
@admin
def forms():
    db=get_db()
    users=_collection("users",300,{"password_hash":0})
    if request.method=="POST":
        from app.routes.forms import slugify, parse_fields
        title=request.form.get("title","").strip()
        fields=parse_fields(request.form.get("fields",""))
        if not title or not fields:
            flash("A form needs a title and at least one field.","error"); return redirect("/admin/forms")
        base=slugify(title); slug=base; i=2
        while db.forms.find_one({"slug":slug}): slug=f"{base}-{i}"; i+=1
        target=request.form.get("target_user_id","").strip() or None
        doc={"_id":new("frm_"),"slug":slug,"title":title,"description":request.form.get("description","").strip(),"fields":fields,"target_user_id":target,"status":"active","created_at":now(),"created_by":"ADMIN"}
        db.forms.insert_one(doc)
        if target:
            from app.repositories.notifications import add
            link=f"/forms/{slug}"
            add(target,f"Form assigned: {title}","An administrator has shared a form with your CIRCULINK account.","form",link,"user")
        _audit("FORM_CREATED",doc["_id"],f"slug={slug};target={target or 'public'}")
        flash(f"Form created. Share /forms/{slug}","success")
        return redirect("/admin/forms")
    forms=list(db.forms.find().sort("created_at",-1).limit(200)) if db is not None else []
    for f in forms:
        f["submission_count"]=db.form_submissions.count_documents({"form_id":f["_id"]}) if db is not None else 0
    return render_template("admin/forms.html",forms=forms,users=users)

@admin_bp.post("/forms/<form_id>/toggle")
@admin
def form_toggle(form_id):
    db=get_db(); f=db.forms.find_one({"_id":form_id}) if db is not None else None
    if not f: flash("Form not found.","error")
    else:
        status="inactive" if f.get("status")=="active" else "active"; db.forms.update_one({"_id":form_id},{"$set":{"status":status,"updated_at":now()}}); _audit("FORM_STATUS",form_id,status); flash("Form status updated.","success")
    return redirect("/admin/forms")

@admin_bp.get("/forms/<form_id>/submissions")
@admin
def form_submissions(form_id):
    db=get_db(); f=db.forms.find_one({"_id":form_id}) if db is not None else None
    if not f: return render_template("error.html",code=404,title="Form not found",message="The form could not be found."),404
    rows=list(db.form_submissions.find({"form_id":form_id}).sort("created_at",-1))
    return render_template("admin/form_submissions.html",form=f,submissions=rows)

@admin_bp.route("/polls", methods=["GET","POST"])
@admin
def polls():
    db=get_db(); users=_collection("users",300,{"password_hash":0})
    if request.method=="POST":
        from app.routes.polls import slugify
        title=request.form.get("title","").strip(); question=request.form.get("question","").strip(); options=[x.strip() for x in request.form.get("options","").splitlines() if x.strip()]
        if not title or not question or len(options)<2: flash("A poll needs a title, question and at least two options.","error"); return redirect("/admin/polls")
        base=slugify(title); slug=base; i=2
        while db.polls.find_one({"slug":slug}): slug=f"{base}-{i}"; i+=1
        target=request.form.get("target_user_id","").strip() or None
        doc={"_id":new("pol_"),"slug":slug,"title":title,"question":question,"options":options,"target_user_id":target,"status":"active","created_at":now(),"created_by":"ADMIN"}
        db.polls.insert_one(doc)
        if target:
            from app.repositories.notifications import add
            add(target,f"Poll assigned: {title}","An administrator has invited you to participate in a CIRCULINK poll.","poll",f"/polls/{slug}","user")
        _audit("POLL_CREATED",doc["_id"],f"slug={slug};target={target or 'public'}"); flash(f"Poll created. Share /polls/{slug}","success"); return redirect("/admin/polls")
    polls=list(db.polls.find().sort("created_at",-1).limit(200)) if db is not None else []
    for p in polls:
        counts={o:db.poll_votes.count_documents({"poll_id":p["_id"],"option":o}) for o in p.get("options",[])}; p["counts"]=counts; p["total_votes"]=sum(counts.values())
    return render_template("admin/polls.html",polls=polls,users=users)

@admin_bp.post("/polls/<poll_id>/toggle")
@admin
def poll_toggle(poll_id):
    db=get_db(); p=db.polls.find_one({"_id":poll_id}) if db is not None else None
    if not p: flash("Poll not found.","error")
    else:
        status="inactive" if p.get("status")=="active" else "active"; db.polls.update_one({"_id":poll_id},{"$set":{"status":status,"updated_at":now()}}); _audit("POLL_STATUS",poll_id,status); flash("Poll status updated.","success")
    return redirect("/admin/polls")

@admin_bp.get("/audit")
@admin
def audit(): return render_template("admin/audit.html",logs=_collection("audit_logs"))

@admin_bp.route("/circular/finance",methods=["GET","POST"])
@admin
def circular_finance():
    from app.services.circular import finance_settings,save_finance
    db=get_db()
    if request.method=="POST":
        try:
            save_finance(request.form); db.settings.update_one({"key":"contributor_levels"},{"$set":{"value":{"intermediate":int(request.form.get("intermediate_level",1500)),"super":int(request.form.get("super_level",5000))}}},upsert=True); flash("Circular finance and contribution rules updated.","success")
        except Exception as exc: flash(str(exc),"error")
    return render_template("admin/circular_finance.html",finance=finance_settings())

@admin_bp.get("/requests")
@admin
def circular_requests(): return render_template("admin/circular_requests.html",requests=_collection("material_requests"),fulfillments=_collection("fulfillments"))

@admin_bp.route("/payouts",methods=["GET","POST"])
@admin
def payouts():
    if request.method=="POST":
        db=get_db(); pid=request.form.get("payout_id"); status=request.form.get("status","PAID"); db.payouts.update_one({"_id":pid},{"$set":{"status":status,"processed_at":now(),"processor_note":request.form.get("note","")}}); _audit("PAYOUT_"+status,pid); flash("Payout updated.","success")
    return render_template("admin/payouts.html",payouts=_collection("payouts"),redemptions=_collection("point_redemptions"))

@admin_bp.route("/certificates",methods=["GET","POST"])
@admin
def certificates():
    db=get_db()
    if request.method=="POST":
        from app.services.compliance import create_certificate
        u=db.users.find_one({"_id":request.form.get("user_id")})
        if u:
            create_certificate(u,request.form.get("certificate_type","COMPLIANCE"),request.form.get("level","BEGINNER"),request.form.get("period","")); flash("Certificate issued with verification QR.","success")
        else: flash("User not found.","error")
    return render_template("admin/circular_certificates.html",certificates=_collection("certificates"),users=_collection("users",300,{"password_hash":0}))

@admin_bp.route("/messages",methods=["GET"])
@admin
def messages(): return render_template("admin/messages.html",messages=_collection("contact_messages"))

@admin_bp.post("/fulfillments/<fid>/verify")
@admin
def admin_verify_fulfillment(fid):
    from app.services.circular import confirm_fulfillment
    db=get_db(); f=db.fulfillments.find_one({"_id":fid}) if db is not None else None
    if not f: flash("Fulfillment not found.","error")
    else:
        try: confirm_fulfillment(fid,f["source_id"]); flash("Fulfillment verified by administrator.","success")
        except Exception as exc: flash(str(exc),"error")
    return redirect("/admin/requests")

@admin_bp.get("/revenue")
@admin
def revenue():
    db=get_db(); rows=list(db.platform_revenue.find().sort("created_at",-1).limit(500)) if db is not None else []; total=round(sum(float(x.get("total_revenue",0)) for x in rows),2)
    return render_template("admin/revenue.html",rows=rows,total=total)
