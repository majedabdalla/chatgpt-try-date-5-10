import uuid
import time
from typing import Optional, Dict


users_online = set()
rooms: Dict[str, dict] = {}
user_to_room: Dict[int, str] = {}


def create_room(user1: int, user2: int) -> str:
room_id = uuid.uuid4().hex[:8]
rooms[room_id] = {
'room_id': room_id,
'users': [user1, user2],
'created_at': time.time(),
'messages': [],
}
user_to_room[user1] = room_id
user_to_room[user2] = room_id
return room_id


def close_room(room_id: str):
room = rooms.pop(room_id, None)
if not room:
return
for uid in room.get('users', []):
user_to_room.pop(uid, None)


def find_match_for(user_id: int, prefer_filters: dict = None) -> Optional[int]:
for candidate in list(users_online):
if candidate != user_id and candidate not in user_to_room:
return candidate
return None


def add_to_pool(user_id: int):
users_online.add(user_id)


def remove_from_pool(user_id: int):
users_online.discard(user_id)
