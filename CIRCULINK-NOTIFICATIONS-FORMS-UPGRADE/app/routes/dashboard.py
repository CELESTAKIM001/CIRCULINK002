from flask import Blueprint, render_template
from app.utils.auth import required,user
from app.repositories.notifications import for_user
from app.repositories.listings import find
from app.db import get_db
from app.services.circular import point_balance, finance_settings
from app.services.compliance import contributor_level

dashboard_bp=Blueprint("dashboard",__name__,url_prefix="/dashboard")

@dashboard_bp.get("/")
@required
def home():
    u=user(); db=get_db()
    certificates=list(db.certificates.find({"owner_id":u["_id"],"status":"VALID"}).sort("issued_at",-1)) if db is not None else []
    requests=list(db.material_requests.find({"company_id":u["_id"]}).sort("created_at",-1).limit(10)) if db is not None and u.get("account_type")=="company" else []
    payouts=list(db.payouts.find({"beneficiary_id":u["_id"]}).sort("created_at",-1).limit(10)) if db is not None else []
    points=point_balance(u["_id"])
    return render_template("dashboard/home.html",user=u,notifications=for_user(u["_id"]),certificates=certificates,requests=requests,payouts=payouts,points=points,level=contributor_level(points),finance=finance_settings())

@dashboard_bp.get("/inventory")
@required
def inventory():
    db=get_db(); uid=user()["_id"]
    listings=list(db.listings.find({"owner_id":uid}).sort("created_at",-1).limit(200)) if db is not None else []
    return render_template("dashboard/inventory.html",listings=listings)
@dashboard_bp.get("/pickups")
@required
def pickups():return render_template("dashboard/pickups.html")
@dashboard_bp.get("/transactions")
@required
def transactions():
    db=get_db(); return render_template("dashboard/transactions.html",transactions=list(db.transactions.find({"user_id":user()["_id"]}).sort("created_at",-1)) if db is not None else [])
