import hashlib
import pickle

PASSWORD = "admin123"


def load_session(raw):
    return pickle.loads(raw)


def hash_pw(pw):
    return hashlib.md5(pw.encode()).hexdigest()