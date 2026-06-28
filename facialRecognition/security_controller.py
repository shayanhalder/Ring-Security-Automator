import requests
from setup import SecurityStatus

REQUEST_TIMEOUT = 10


class SecurityController:
    def __init__(self, test_mode: bool, initial_status=SecurityStatus.DISARMED):
        self.test_mode = test_mode
        self.security_status = initial_status
        self.API_URL = "http://localhost:3000"

    def _parse_api_response(self, response: requests.Response, action: str) -> dict | None:
        try:
            data = response.json()
        except requests.JSONDecodeError:
            print(f"[ERROR] {action}: non-JSON response (HTTP {response.status_code})")
            return None

        if not response.ok or not data.get("success"):
            message = data.get("message", response.status_code)
            print(f"[ERROR] {action}: {message}")
            return None

        return data

    def _request(self, method: str, path: str, action: str) -> dict | None:
        try:
            response = requests.request(
                method,
                f"{self.API_URL}{path}",
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as e:
            print(f"[ERROR] {action}: request failed: {e}")
            return None

        return self._parse_api_response(response, action)

    def get_security_status(self) -> SecurityStatus | None:
        data = self._request("GET", "/get-security-status", "get security status")
        if data is None:
            return None

        try:
            return SecurityStatus(data["security_status"])
        except (KeyError, ValueError) as e:
            print(f"[ERROR] get security status: invalid response: {e}")
            return None

    def set_test_mode(self, test_mode: bool):
        self.test_mode = test_mode

    def arm_security_away(self) -> bool:
        print("[INFO] Arming security...")
        if self.test_mode:
            print("[INFO] Security armed")
            self.security_status = SecurityStatus.AWAY
            return True

        if self._request("POST", "/arm-security-away", "arm security away") is None:
            return False

        self.security_status = SecurityStatus.AWAY
        print("[INFO] Security armed")
        return True

    def disarm_security(self) -> bool:
        print("[INFO] Disarming security...")
        if self.test_mode:
            print("[INFO] Security disarmed")
            self.security_status = SecurityStatus.DISARMED
            return True

        if self._request("POST", "/disarm-security", "disarm security") is None:
            return False

        self.security_status = SecurityStatus.DISARMED
        print("[INFO] Security disarmed")
        return True

    def arm_security_home(self) -> bool:
        print("[INFO] Arming security home...")
        if self.test_mode:
            print("[INFO] Security home armed")
            self.security_status = SecurityStatus.HOME
            return True

        if self._request("POST", "/arm-security-home", "arm security home") is None:
            return False

        self.security_status = SecurityStatus.HOME
        print("[INFO] Security home armed")
        return True
