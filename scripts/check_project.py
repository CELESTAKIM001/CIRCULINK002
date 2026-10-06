from pathlib import Path
r=Path(__file__).resolve().parents[1]
required=['api/index.py','vercel.json','.env.example','static/img/logo.png','templates/landing.html']
print('PASS' if all((r/x).exists() for x in required) else 'FAIL')
print('FILES',sum(p.is_file() for p in r.rglob('*')))
