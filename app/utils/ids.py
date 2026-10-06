import uuid
def new(prefix=""): return prefix+uuid.uuid4().hex
