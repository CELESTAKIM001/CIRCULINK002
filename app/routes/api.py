from flask import Blueprint,jsonify,request,Response,current_app
from math import radians, sin, cos, asin, sqrt
from app.db import get_db
from app.services.catalog import CATEGORIES,MATERIALS
from app.services.matching import match
api_bp=Blueprint("api",__name__,url_prefix="/api")

@api_bp.get("/media/<media_id>")
def media(media_id):
    import base64
    db=get_db()
    item=db.media.find_one({"_id":media_id}) if db is not None else None
    if not item: return jsonify(ok=False,error="Media not found"),404
    try: raw=base64.b64decode(item.get("data", ""))
    except Exception: return jsonify(ok=False,error="Media is invalid"),500
    return Response(raw,mimetype=item.get("content_type","image/webp"),headers={"Cache-Control":"public, max-age=31536000, immutable","X-Content-Type-Options":"nosniff"})

@api_bp.get("/cron/media-cleanup")
def media_cleanup():
    from app.services.media_retention import cleanup
    expected=current_app.config.get("CRON_SECRET") or ""
    supplied=request.headers.get("Authorization","").replace("Bearer ","").strip() or request.args.get("secret","")
    if not expected or supplied != expected: return jsonify(ok=False,error="Unauthorized"),401
    return jsonify(ok=True,**cleanup(12))

@api_bp.get("/health")
def health():
    from app.db import get_db
    db = get_db()
    db_ok = False
    if db is not None:
        try:
            db.command("ping")
            db_ok = True
        except Exception:
            current_app.logger.exception("Health check MongoDB ping failed")
    status = "ready" if db_ok else "degraded"
    return jsonify(ok=db_ok, service="CIRCULINK", status=status, database="connected" if db_ok else "unavailable", retryable=not db_ok), (200 if db_ok else 503)
@api_bp.get("/materials")
def materials():return jsonify(ok=True,categories=CATEGORIES,materials=MATERIALS)
@api_bp.get("/matches")
def matches():return jsonify(ok=True,items=match(request.args.get("material",""),request.args.get("category","")))
@api_bp.get("/map/locations")
def locations():
    points=[{"name":"Campus collection point","type":"campus","lat":-1.286389,"lng":36.817223},{"name":"Event collection point","type":"event","lat":-1.292066,"lng":36.821945},{"name":"Custom business point","type":"business","lat":-1.278,"lng":36.812}]
    db=get_db()
    if db is not None:
        for x in db.listings.find({"status":"active","location.lat":{"$ne":None},"location.lng":{"$ne":None}}, {"title":1,"location":1}).limit(100):
            loc=x.get("location") or {}
            if loc.get("lat") is not None and loc.get("lng") is not None:
                points.append({"name":x.get("title","Listing"),"type":"listing","lat":loc["lat"],"lng":loc["lng"]})
    return jsonify(ok=True,locations=points)

@api_bp.get("/map/nearby")
def nearby():
    try: lat=float(request.args["lat"]); lng=float(request.args["lng"]); radius=float(request.args.get("km",25))
    except (KeyError,ValueError): return jsonify(ok=False,error="lat, lng and optional km are required"),400
    db=get_db(); results=[] if db is None else list(db.listings.find({"status":"active","location.lat":{"$ne":None},"location.lng":{"$ne":None}}).limit(250))
    def dist(a,b,c,d):
        p=radians(a); q=radians(c); dp=radians(c-a); dl=radians(d-b); h=sin(dp/2)**2+cos(p)*cos(q)*sin(dl/2)**2; return 6371*2*asin(sqrt(h))
    out=[]
    for x in results:
        loc=x.get("location") or {}; d=dist(lat,lng,float(loc.get("lat")),float(loc.get("lng")))
        if d<=radius: out.append({"id":x["_id"],"title":x.get("title"),"distance_km":round(d,2),"image":x.get("primary_image"),"lat":loc.get("lat"),"lng":loc.get("lng")})
    out.sort(key=lambda z:z["distance_km"]); return jsonify(ok=True,items=out)
