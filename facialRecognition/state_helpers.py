from setup import SecurityStatus

def is_home(name: str, states: dict, LEFT_THRESHOLD: int):
    return states[name]['last_x'] < LEFT_THRESHOLD and not states[name]['currently_in_frame'] and states[name]['logged_exit']

def is_away(name: str, states: dict, RIGHT_THRESHOLD: int):
    return states[name]['last_x'] > RIGHT_THRESHOLD and not states[name]['currently_in_frame'] and states[name]['logged_exit']


def handle_admin_exits(admin_states: dict, LEFT_THRESHOLD: int, RIGHT_THRESHOLD: int): #, currently_in_frame: dict):
    for name, info in list(admin_states.items()):
        last_x = info['last_x']
        if last_x < LEFT_THRESHOLD and not admin_states[name]['currently_in_frame'] and not admin_states[name]['logged_exit']:
            print(f"-----[INFO]----- {name} exited left")
            admin_states[name]['logged_exit'] = True
        elif last_x > RIGHT_THRESHOLD and not admin_states[name]['currently_in_frame'] and not admin_states[name]['logged_exit']:
            print(f"-----[INFO]----- {name} exited right")
            admin_states[name]['logged_exit'] = True


def arm_security_condition(admin_states: dict, security_status: SecurityStatus, RIGHT_THRESHOLD: int, LEFT_THRESHOLD: int):
    return all(is_away(name, admin_states, RIGHT_THRESHOLD) for name in list(admin_states.keys())) and security_status != SecurityStatus.ARMED_AWAY
        
def disarm_security_condition(admin_states: dict, security_status: SecurityStatus, RIGHT_THRESHOLD: int, LEFT_THRESHOLD: int):
    return any(is_home(name, admin_states, LEFT_THRESHOLD) for name in list(admin_states.keys())) and security_status == SecurityStatus.ARMED_AWAY


