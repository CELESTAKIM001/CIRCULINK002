from app.repositories.listings import find
def match(material,category=""): return find(material,category)[:20]
