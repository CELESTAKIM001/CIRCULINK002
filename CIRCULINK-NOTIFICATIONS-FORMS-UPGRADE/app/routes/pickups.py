from flask import Blueprint,render_template,request,redirect,flash
from app.utils.auth import required,user
from app.services.pickups import create
pickups_bp=Blueprint("pickups",__name__,url_prefix="/pickups")
@pickups_bp.route("/schedule",methods=["GET","POST"])
@required
def schedule():
    if request.method=="POST":create(request.form,user()["_id"]);flash("Pickup request submitted.","success");return redirect("/dashboard/pickups")
    return render_template("dashboard/schedule.html")
