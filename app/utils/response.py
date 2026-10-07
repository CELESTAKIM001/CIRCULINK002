from flask import jsonify
def ok(**x): return jsonify({"ok":True,**x})
def fail(message,status=400,**x): return jsonify({"ok":False,"error":message,**x}),status
