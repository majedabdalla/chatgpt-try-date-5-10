
from datetime import datetime
from storage import load_users, save_users

def build_metadata_text(room: dict, sender_profile: dict, receiver_profile: dict):
    created = datetime.utcfromtimestamp(room.get('created_at', 0)).isoformat()
    lines = [f"📢 Room #{room.get('room_id')}", f"🕒 Created: {created}", '']
    lines.append(f"👤 Sender: {sender_profile.get('user_id')} (username: @{sender_profile.get('username','N/A')}, phone: {sender_profile.get('phone_number') or 'N/A'})")
    if receiver_profile:
        lines.append(f"👥 Receiver: {receiver_profile.get('user_id')} (username: @{receiver_profile.get('username','N/A')}, phone: {receiver_profile.get('phone_number') or 'N/A'})")
    return "\n".join(lines)

def approve_premium(user_id: int):
    users = load_users()
    p = users.get(str(user_id))
    if not p:
        return False
    expiry = (datetime.utcnow()).isoformat()
    p['is_premium'] = True
    p['premium_expiry'] = expiry
    users[str(user_id)] = p
    save_users(users)
    return True
