import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'master'))
import database

def verify_pin():
    print("Initializing DB...")
    database.init_db()
    
    state = database.get_state()
    current_pin = state.get('pin')
    print(f"Initial PIN in DB: {current_pin}")
    
    if current_pin != '1234':
        print("Note: PIN is already changed or default was different.")
    
    print("Setting new PIN to '9999'...")
    database.set_state('pin', '9999')
    
    state = database.get_state()
    new_pin = state.get('pin')
    print(f"New PIN in DB: {new_pin}")
    
    if new_pin == '9999':
        print("SUCCESS: PIN updated in database.")
    else:
        print("FAILURE: PIN not updated.")

    # Reset to 1234 for user consistency during testing if they expect it
    print("Resetting PIN to '1234' for user convenience...")
    database.set_state('pin', '1234')

if __name__ == "__main__":
    verify_pin()
