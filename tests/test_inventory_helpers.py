def test_vercel_config_has_cron():
 import json
 with open("vercel.json",encoding="utf-8") as f: cfg=json.load(f)
 assert any(x.get("path")=="/api/cron/media-cleanup" for x in cfg.get("crons",[]))

def test_env_has_security_settings():
 text=open(".env.example",encoding="utf-8").read()
 assert "SECRET_KEY=" in text and "CRON_SECRET=" in text and "SESSION_COOKIE_SECURE=true" in text
