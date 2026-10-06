from datetime import datetime, timezone
from flask import Blueprint, render_template, request, flash, redirect, jsonify, current_app
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
    allowed={"users","listings","plans","notifications","material_requests","fulfillments","payouts","point_redemptions","certificates","contact_messages"}
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


def _reconcile_transaction(db, tx):
    """Query Safaricom for one pending STK transaction and persist the result."""
    from app.services.mpesa import query_stk
    from app.routes.payments import _finalize_paid

    checkout_id = tx.get("checkout_request_id")
    if not checkout_id:
        return {"ok": False, "status": tx.get("status"), "error": "No CheckoutRequestID is stored for this transaction."}

    q = query_stk(checkout_id)
    data = q.get("data") or {}
    code = data.get("ResultCode")
    update = {
        "provider_query": data,
        "last_reconciled_at": now(),
        "updated_at": now(),
    }
    if q.get("ok") and code is not None:
        try:
            code_int = int(code)
        except (TypeError, ValueError):
            code_int = 99
        if code_int == 0:
            receipt = tx.get("mpesa_receipt") or data.get("MpesaReceiptNumber")
            order = db.orders.find_one({"_id": tx.get("order_id")})
            if receipt and order:
                _finalize_paid(db, tx, order, receipt, data)
                return {"ok": True, "status": "paid", "receipt": receipt}
        elif code_int not in (1037, 4999, 1):
            update["status"] = "failed"
            update["failure_reason"] = data.get("ResultDesc") or "Safaricom reported a failed STK transaction."
    db.transactions.update_one({"_id": tx["_id"]}, {"$set": update})
    return {"ok": bool(q.get("ok")), "status": update.get("status", tx.get("status")), "provider_message": data.get("ResultDesc") or q.get("error")}


@admin_bp.post("/payments/<tx_id>/reconcile")
@admin
def reconcile_payment(tx_id):
    db = get_db()
    tx = db.transactions.find_one({"_id": tx_id}) if db is not None else None
    if not tx:
        return jsonify(ok=False, error="Transaction not found."), 404
    if tx.get("status") == "paid":
        return jsonify(ok=True, status="paid", message="Transaction is already confirmed."), 200
    result = _reconcile_transaction(db, tx)
    _audit("PAYMENT_RECONCILED", tx_id, result.get("provider_message", result.get("status", "")))
    return jsonify(result), 200 if result.get("ok") else 502


@admin_bp.post("/payments/reconcile-pending")
@admin
def reconcile_pending_payments():
    db = get_db()
    if db is None:
        return jsonify(ok=False, error="Payment database is unavailable."), 503
    pending = list(db.transactions.find({
        "status": {"$in": ["awaiting_callback", "processing", "pending"]},
        "checkout_request_id": {"$exists": True, "$ne": ""},
    }).sort("created_at", -1).limit(50))
    results = []
    for tx in pending:
        try:
            results.append({"id": tx["_id"], **_reconcile_transaction(db, tx)})
        except Exception as exc:
            current_app.logger.exception("Payment reconciliation failed for %s", tx.get("_id"))
            results.append({"id": tx["_id"], "ok": False, "error": str(exc)})
    _audit("PAYMENTS_RECONCILED", "PENDING", f"Processed {len(results)} pending transactions")
    return jsonify(ok=True, count=len(results), results=results), 200

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
def notifications(): return render_template("admin/notifications.html",notifications=_collection("notifications"))

@admin_bp.post("/notifications/create")
@admin
def notification_create():
    db=get_db()
    if db is not None:
        db.notifications.insert_one({"_id":new("not_"),"title":request.form.get("title",""),"message":request.form.get("message",""),"status":"active","created_at":now()}); _audit("NOTIFICATION_CREATED")
        flash("Notification created.","success")
    return redirect("/admin/notifications")

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
