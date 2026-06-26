import requests 
from setup import SecurityStatus

class SecurityController:
    def __init__(self, test_mode: bool, initial_status=SecurityStatus.DISARMED):
        self.test_mode = test_mode
        self.security_status = initial_status
        self.API_URL = "http://localhost:3000"

    def get_security_status(self):
        return self.security_status

    def set_test_mode(self, test_mode: bool):
        self.test_mode = test_mode

    def arm_security_away(self) -> bool:
        print("[INFO] Arming security...")
        if self.test_mode:
            print("[INFO] Security armed")
            self.security_status = SecurityStatus.ARMED_AWAY
            return True

        response = requests.post(f"{self.API_URL}/arm-security-away") 
        status = response.json()['success']
        if not status:
            print("[ERROR] Failed to arm security")
            return False

        self.security_status = SecurityStatus.ARMED_AWAY
        print("[INFO] Security armed")
        return True

    def disarm_security(self) -> bool:
        print("[INFO] Disarming security...")
        if self.test_mode:
            print("[INFO] Security disarmed")
            self.security_status = SecurityStatus.DISARMED
            return True

        response = requests.post(f"{self.API_URL}/disarm-security")
        status = response.json()['success']
        if not status:
            print("[ERROR] Failed to disarm security")
            return False
        
        self.security_status = SecurityStatus.DISARMED
        print("[INFO] Security disarmed")
        return True

    def arm_security_home(self) -> bool:
        print("[INFO] Arming security home...")
        if self.test_mode:
            print("[INFO] Security home armed")
            self.security_status = SecurityStatus.ARMED_HOME
            return True

        response = requests.post(f"{self.API_URL}/arm-security-home")
        status = response.json()['success']
        if not status:
            print("[ERROR] Failed to arm security home")
            return False
        
        self.security_status = SecurityStatus.ARMED_HOME
        print("[INFO] Security home armed")
        return True

    # def get_security_status(self):
    #     if self.test_mode:
    #         return None

    #     response = requests.get(f"{self.API_URL}/get-security-status")
    #     data = response.json()
    #     return data['security_status']
