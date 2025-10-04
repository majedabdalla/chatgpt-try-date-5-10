from datetime import datetime, timedelta
from typing import Optional
from storage import load_users, save_users
import logging


logger = logging.getLogger(__name__)




def build_metadata_text(room: dict, sender_profile: dict, receiver_profile: Optional[dict]):
created = datetime.utcfromtimestamp(room.get('created_at', 0)).isoformat()
lines = [f"📢 Room #{room.get('room_id')}", f"🕒 Created: {created}", '']
lines.append(f"👤 Sender: {sender_profile.get('user_id')} (username: @{sender_profile.get('username','N/A')}, phone: {sender_profile.get('phone_number') or 'N/A'})")
if receiver_profile:
lines.append(f"👥 Receiver: {receiver_profile.get('user_id')} (username: @{receiver_profile.get('username','N/A')}, phone: {receiver_profile.get('phone_number') or 'N/A'})")
return "\n".join(lines)




def approve_premium(user_id: int, days: int = 90) -> bool:
"""Approve a user for premium for `days` days from now."""
users = load_users()
p = users.get(str(user_id))
if not p:
return False
expiry = (datetime.utcnow() + timedelta(days=days)).isoformat()
p['is_premium'] = True
p['premium_expiry'] = expiry
users[str(user_id)] = p
save_users(users)
return True




async def revoke_expired_job(context):
"""JobQueue callback to revoke expired premiums and notify admin group if revocations occurred."""
try:
users = load_users()
now = datetime.utcnow()
revoked = []
for uid, profile in list(users.items()):
exp = profile.get('premium_expiry')
if not exp:
continue
try:
exp_dt = datetime.fromisoformat(exp)
except Exception:
continue
if exp_dt < now:
profile['is_premium'] = False
profile['premium_expiry'] = None
users[uid] = profile
revoked.append(uid)
if revoked:
save_users(users)
tg = int(context.bot_data.get('TARGET_GROUP_ID') or 0)
text = f"[Auto-Revoke] Revoked premium for {len(revoked)} users: {', '.join(revoked)}"
try:
await context.bot.send_message(chat_id=tg, text=text)
except Exception:
logger.exception('Failed to send revoke report to admin group')
except Exception:
logger.exception('Error in revoke_expired_job')
