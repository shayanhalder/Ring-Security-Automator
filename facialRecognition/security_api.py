import requests 

API_URL = "http://localhost:3000"

def arm_security_away() -> bool:
    print("[INFO] Arming security...")
    response = requests.get(f"{API_URL}/arm-security-away")
    status = response.json()['success']
    if not status:
        print("[ERROR] Failed to arm security")
        return False
    
    print("[INFO] Security armed")
    return True

def disarm_security() -> bool:
    print("[INFO] Disarming security...")
    response = requests.get(f"{API_URL}/disarm-security")
    status = response.json()['success']
    if not status:
        print("[ERROR] Failed to disarm security")
        return False
    
    print("[INFO] Security disarmed")
    return True

def arm_security_home() -> bool:
    print("[INFO] Arming security home...")
    response = requests.get(f"{API_URL}/arm-security-home")
    status = response.json()['success']
    if not status:
        print("[ERROR] Failed to arm security home")
        return False
    
    print("[INFO] Security home armed")
    return True

def get_security_status():
    response = requests.get(f"{API_URL}/get-security-status")
    data = response.json()
    return data['security_status']
    # return response.json()
