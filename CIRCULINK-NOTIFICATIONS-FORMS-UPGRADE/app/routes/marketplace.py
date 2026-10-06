import json
from flask import Blueprint, render_template, request, redirect, flash
from app.utils.auth import required, user
from app.repositories.listings import find, one, add
from app.repositories.orders import create
from app.services.media import upload

marketplace_bp = Blueprint("marketplace", __name__, url_prefix="/marketplace")

@marketplace_bp.get("/")
def index():
    return render_template("marketplace/index.html", listings=find(request.args.get("q", ""), request.args.get("category", "")))

@marketplace_bp.get("/listing/<id>")
def listing(id):
    item = one(id)
    if not item:
        return render_template("error.html", code=404, title="Material not found", message="This marketplace listing is no longer available or has been removed.", retry_url="/marketplace/", retry_label="Return to marketplace"), 404
    return render_template("marketplace/listing.html", item=item)

@marketplace_bp.route("/add", methods=["GET", "POST"])
@required
def add_page():
    if request.method == "POST":
        try:
            files = [f for f in request.files.getlist("images") if f and f.filename]
            if not files:
                raise ValueError("At least one real listing photo is required.")
            images = [upload(f) for f in files[:5]]
            add(request.form, user()["_id"], images)
            flash("Material published with real marketplace photos.", "success")
            return redirect("/marketplace/")
        except Exception as exc:
            flash(str(exc) or "The listing could not be published.", "error")
    return render_template("marketplace/add.html")

@marketplace_bp.post("/checkout")
@required
def checkout():
    try:
        items = json.loads(request.form.get("items", "[]"))
        if not isinstance(items, list) or not items:
            raise ValueError("Your cart is empty. Add a material before checking out.")
        total = sum(float(i.get("line_total", 0)) for i in items)
        if total <= 0:
            raise ValueError("The checkout total must be greater than zero.")
        o = create(user()["_id"], items, total)
        return redirect("/pay/" + o["_id"])
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        flash(str(exc) or "We could not create the checkout.", "error")
        return redirect("/marketplace/")
    except Exception:
        from flask import current_app
        current_app.logger.exception("Checkout creation failed")
        flash("We could not create your checkout right now. Your cart was not charged.", "error")
        return redirect("/marketplace/")
