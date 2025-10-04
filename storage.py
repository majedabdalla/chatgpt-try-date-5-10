import json
json.dump(data, tmp, ensure_ascii=False, indent=2)
tmp.flush()
os.fsync(tmp.fileno())
finally:
tmp.close()
os.replace(tmp.name, path)


def load_json(path: Path, default=None):
if default is None:
default = {}
try:
if path.exists():
with open(path, 'r', encoding='utf-8') as f:
return json.load(f)
except Exception:
return default
return default


# JSON-based functions (sync)
def save_users(data: Dict[str, Any]):
_atomic_write(USER_FILE, data)


def save_rooms(data: Dict[str, Any]):
_atomic_write(ROOMS_FILE, data)


def load_users() -> Dict[str, Any]:
return load_json(USER_FILE, {})


def load_rooms() -> Dict[str, Any]:
return load_json(ROOMS_FILE, {})


# Optional Supabase client
_supabase = None
if _HAS_SUPABASE and create_client is not None:
try:
_supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception:
_supabase = None


# Helpers for Supabase-backed operations (sync functions wrapped with asyncio.to_thread where needed)
def _supabase_get_all_users():
if not _supabase:
raise RuntimeError('Supabase not configured')
resp = _supabase.table('users').select('*').execute()
return {str(row['user_id']): row for row in (resp.data or [])}


def _supabase_upsert_user(user_id: int, profile: Dict[str, Any]):
if not _supabase:
raise RuntimeError('Supabase not configured')
data = {**profile, 'user_id': int(user_id)}
resp = _supabase.table('users').upsert(data).execute()
return resp


# Async-aware wrappers for handlers
async def load_users_async() -> Dict[str, Any]:
if _supabase:
return await asyncio.to_thread(_supabase_get_all_users)
return await asyncio.to_thread(load_users)


async def save_user_async(user_id: int, profile: Dict[str, Any]):
if _supabase:
return await asyncio.to_thread(_supabase_upsert_user, user_id, profile)
users = await asyncio.to_thread(load_users)
users[str(user_id)] = profile
await asyncio.to_thread(save_users, users)
return True


async def load_rooms_async():
return await asyncio.to_thread(load_rooms)


async def save_rooms_async(data):
return await asyncio.to_thread(save_rooms, data)
