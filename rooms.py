import uuid, time
from db import db, insert_room, get_room, update_room
from models import default_room

users_online = set()  # Keep in memory for now

async def create_room(user1: int, user2: int):
    room_id = uuid.uuid4().hex[:8]
    room_data = default_room(room_id, user1, user2)
    await insert_room(room_data)
    users_online.discard(user1)
    users_online.discard(user2)
    return room_id

async def close_room(room_id: str):
    await update_room(room_id, {"active": False})

async def find_match_for(user_id: int, prefer_filters=None):
    # Prefer filters: gender, region, country, premium_only
    candidates = [uid for uid in users_online if uid != user_id]
    # TODO: Use DB to filter based on matching_preferences
    # For now, just pick the first available
    return candidates[0] if candidates else None

def add_to_pool(user_id: int):
    users_online.add(user_id)

def remove_from_pool(user_id: int):
    users_online.discard(user_id)