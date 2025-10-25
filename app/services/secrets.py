import os 
def get_secret(name: str) -> str: 
    val = os.getenv(name) 
    if not val: 
        raise RuntimeError(f"Missing secret {name}") 
    return val