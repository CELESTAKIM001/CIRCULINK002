from bson import ObjectId
def safe(v):
    if isinstance(v,ObjectId): return str(v)
    if isinstance(v,dict): return {k:safe(x) for k,x in v.items()}
    if isinstance(v,list): return [safe(x) for x in v]
    return v
