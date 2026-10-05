import re
def phone(v):
    p=re.sub(r"\D","",v or ""); return "254"+p[1:] if p.startswith("0") else p
def email(v): return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$",v or ""))
