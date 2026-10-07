from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.repositories.users import create, by_email, check
from app.services.otp import issue, verify
from app.utils.auth import login, logout
from app.utils.validation import phone, email
from app.db import get_db

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        d = request.form.to_dict()
        d["email"] = d.get("email", "").lower().strip()
        if not email(d["email"]):
            flash("Enter a valid email address.", "error")
            return render_template("auth/register.html")
        if get_db() is None:
            flash("Registration is temporarily unavailable because the database is not connected.", "error")
            return render_template("auth/register.html"), 503
        if by_email(d["email"]):
            flash("That email is already registered. Sign in instead.", "error")
            return render_template("auth/register.html")
        try:
            d["phone"] = phone(d.get("phone"))
            u = create(d)
            delivered = issue(u["email"])
            if delivered:
                flash("Account created. Check your email for the verification code.", "success")
            else:
                flash("Account created, but the verification email could not be delivered yet. Use resend when email service is available.", "warning")
            return redirect(url_for("auth.verify_page", email=u["email"]))
        except ValueError as exc:
            flash(str(exc), "error")
        except Exception:
            flash("We could not create the account. Please try again.", "error")
    return render_template("auth/register.html")


@auth_bp.route("/verify", methods=["GET", "POST"])
def verify_page():
    e = request.args.get("email") or request.form.get("email")
    if request.method == "POST":
        if get_db() is None:
            flash("Verification is temporarily unavailable.", "error")
            return render_template("auth/verify.html", email=e), 503
        if verify(e, request.form["code"]):
            get_db().users.update_one({"email": e}, {"$set": {"verified": True}})
            flash("Email verified. You can now sign in.", "success")
            return redirect(url_for("auth.login_page"))
        flash("Invalid or expired code.", "error")
    return render_template("auth/verify.html", email=e)


@auth_bp.post("/resend")
def resend():
    try:
        delivered = issue(request.form["email"])
        flash("A new code was sent." if delivered else "The verification code was generated, but email delivery is currently unavailable.", "success" if delivered else "warning")
    except ValueError as exc:
        flash(str(exc), "error")
    except Exception:
        flash("We could not send another code right now.", "error")
    return redirect(url_for("auth.verify_page", email=request.form["email"]))


@auth_bp.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        if get_db() is None:
            flash("Sign-in is temporarily unavailable because the database is not connected.", "error")
            return render_template("auth/login.html"), 503
        u = by_email(request.form["email"])
        if not u or not check(u, request.form["password"]):
            flash("Email or password is incorrect.", "error")
        elif not u["verified"]:
            flash("Verify your email first.", "error")
        else:
            login(u)
            return redirect("/admin/" if u["role"] == "ADMIN" else "/dashboard/")
    return render_template("auth/login.html")


@auth_bp.get("/logout")
def logout_page():
    logout()
    return redirect("/")
