# api.py - WHISPERCHAIN SERVER (Thin Routing Layer)

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import os
import json

from database import get_connection, init_db
from config import get_config
from game_flow import (
        RoomManager,
        STARTING_SIGNAL,
        MIN_PLAYERS,
        MAX_PLAYERS,
        READY_THRESHOLD
        )

# ============================================
# INIT
# ============================================
config = get_config()

app = Flask(__name__, static_folder='frontend', static_url_path='')
app.config['SECRET_KEY'] = config.SECRET_KEY
CORS(app, resources={
    r"/*": {
        "origins": config.SOCKETIO_CORS_ALLOWED_ORIGINS,
        "methods": ["GET", "POST", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})
socketio = SocketIO(
    app, 
    cors_allowed_origins=config.SOCKETIO_CORS_ALLOWED_ORIGINS,
    async_mode='eventlet'  # Changed from 'threading' to match requirements.txt
)
# ============================================
# STATE
# ============================================
users = {}
sid_to_user = {}
room_manager = RoomManager()


# ============================================
# UTILITIES
# ============================================
def cleanup_temp_users():
    """Remove all temporary users from database on startup."""
    conn = get_connection()
    if not conn:
        return

    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE is_temporary = TRUE")
        deleted = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
        print(f"[CLEANUP] Removed {deleted} temporary users from DB")
    except Exception as e:
        print(f"[ERROR] Cleanup failed: {e}")


def delete_user_from_db(uid, username):
    """Delete user from database."""
    try:
        conn = get_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM users WHERE id = %s", (uid,))
            deleted = cur.rowcount
            conn.commit()
            cur.close()
            conn.close()
            if deleted:
                print(f"[DB] Deleted user {username} (id={uid})")
            else:
                print(f"[DB] User {uid} not found in DB")
        else:
            print(f"[DB] No connection, could not delete {username}")
    except Exception as e:
        print(f"[ERROR] Failed to delete user {uid}: {e}")


def load_user_from_db(uid):
    """Load user from database into memory dict format."""
    try:
        conn = get_connection()
        if not conn:
            return None

        cur = conn.cursor()
        cur.execute("""
            SELECT id, username, signal_strength, is_temporary
            FROM users WHERE id = %s
        """, (uid,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row:
            return {
                    'username': row[1],
                    'signal': row[2],
                    'room': None,
                    'is_temporary': row[3],
                    'sid': None,
                    'session_games': []
                    }
        return None
    except Exception as e:
        print(f"[ERROR] Failed to load user {uid}: {e}")
        return None


def save_game_to_db(game_data):
    """
    Save game to database and return the game ID.
    Returns: game_id or None on failure
    """
    try:
        conn = get_connection()
        if not conn:
            print("[SAVE] No DB connection")
            return None

        cur = conn.cursor()
        cur.execute('''
            INSERT INTO games_history (room_code, num_players, rounds, player_results, player_ids, closed_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            RETURNING id
        ''', (
            game_data.get('room_code', '???'),
            game_data.get('num_players', 1),
            json.dumps(game_data.get('rounds', [])),
            json.dumps(game_data.get('player_results', [])),
            json.dumps(game_data.get('player_ids', []))
            ))

        game_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        print(f"[SAVE] Game {game_id} saved to DB")
        return game_id

    except Exception as e:
        print(f"[SAVE] Error: {e}")
        return None


# ============================================
# HTTP: USER
# ============================================
@app.route('/api/user', methods=['POST'])
def create_user():
    data = request.get_json()
    username = data.get('username', '').strip()

    if not username:
        return jsonify({'error': 'Username required'}), 400

    if len(username) < 3:
        return jsonify({'error': 'Username must be at least 3 characters'}), 400

    if len(username) > 20:
        return jsonify({'error': 'Username too long (max 20)'}), 400

    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    cur = conn.cursor()

    try:
        # Check if username exists
        cur.execute("""
            SELECT id, is_temporary FROM users WHERE username = %s
        """, (username,))
        existing = cur.fetchone()

        if existing:
            existing_id, is_temp = existing
            if is_temp:
                # Stale temporary user - delete and allow reuse
                cur.execute("DELETE FROM users WHERE id = %s", (existing_id,))
                print(f"[USER] Cleaned stale temp user: {username} (id={existing_id})")
            else:
                # Permanent user - reject
                return jsonify({'error': 'Username already taken'}), 400

        # Insert temporary user
        cur.execute("""
            INSERT INTO users (username, signal_strength, is_temporary)
            VALUES (%s, %s, TRUE)
            RETURNING id, username, signal_strength
        """, (username, STARTING_SIGNAL))

        row = cur.fetchone()
        conn.commit()

        user_id = row[0]

        # Store in memory with session_games tracking
        users[user_id] = {
                'username': row[1],
                'signal': row[2],
                'room': None,
                'is_temporary': True,
                'sid': None,
                'session_games': []
                }

        print(f"[USER+] {row[1]} (id={user_id}, signal={row[2]})")

        return jsonify({
            'id': user_id,
            'username': row[1],
            'signal_strength': row[2]
            })

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] User creation failed: {e}")
        return jsonify({'error': 'Failed to create user'}), 500

    finally:
        cur.close()
        conn.close()


@app.route('/api/user/<int:uid>', methods=['DELETE'])
def delete_user(uid):
    if uid in users:
        print(f"[USER-] {users[uid]['username']}")
        del users[uid]
    return jsonify({'status': 'ok'})


# ============================================
# HTTP: ROOMS
# ============================================
@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    return jsonify(room_manager.get_all_rooms())


@app.route('/api/rooms', methods=['POST'])
def create_room():
    code = room_manager.create_room()
    if not code:
        return jsonify({'error': 'Room limit reached'}), 503
    print(f"[ROOM+] {code}")
    return jsonify({'code': code})


# ============================================
# HTTP: HISTORY (SECURED)
# ============================================
@app.route('/api/history', methods=['GET'])
def get_history():
    user_id = request.args.get('user_id', type=int)

    try:
        if not user_id:
            print("[HISTORY] Missing user_id")
            return jsonify([])

        conn = get_connection()
        if not conn:
            print("[HISTORY] No DB connection")
            return jsonify([])

        cur = conn.cursor()

        cur.execute("""
            SELECT id, room_code, num_players, rounds, player_results, created_at, closed_at
            FROM games_history
            WHERE player_ids @> %s::jsonb
            ORDER BY closed_at DESC
        """, (json.dumps([user_id]),))

        rows = cur.fetchall()
        cur.close()
        conn.close()

        games = []
        for r in rows:
            games.append({
                'id': r[0],
                'room_code': r[1],
                'num_players': r[2],
                'rounds': r[3] if r[3] else [],
                'player_results': r[4] if r[4] else [],
                'created_at': r[5].isoformat() if r[5] else None,
                'closed_at': r[6].isoformat() if r[6] else None
            })

        print(f"[HISTORY] Returning {len(games)} games for user {user_id}")
        return jsonify(games)

    except Exception as e:
        print(f"[HISTORY] Error: {e}")
        return jsonify([])


@app.route('/api/history', methods=['POST'])
def save_history():
    """Legacy endpoint - kept for compatibility but server now saves automatically."""
    data = request.get_json()

    game_id = save_game_to_db(data)

    if game_id:
        return jsonify({'id': game_id, 'status': 'saved'})
    else:
        return jsonify({'error': 'Failed to save'}), 500


# ============================================
# WEBSOCKET: CONNECTION
# ============================================
@socketio.on('connect')
def on_connect():
    print(f"[WS] connect: {request.sid}")


@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    uid = sid_to_user.get(sid)

    print(f"[WS] disconnect: sid={sid}, uid={uid}")

    if uid and uid in users:
        user = users[uid]
        username = user.get('username', 'Unknown')
        code = user.get('room')
        is_temporary = user.get('is_temporary', True)

        print(f"[WS] DISCONNECT - {username} (temp={is_temporary}, room={code})")

        # Remove from game room if in one
        if code:
            room = room_manager.get_room(code)
            if room:
                # Update signal in original_players before removing
                if hasattr(room, 'original_players'):
                    for p in room.original_players:
                        if p['user_id'] == uid:
                            p['signal'] = users[uid]['signal']
                            break

                room.remove_player(uid)

                socketio.emit('player_left', {
                    'players': room.get_player_list()
                    }, room=code)

                # Handle different scenarios
                if not room.players:
                    # Room is completely empty - end game and delete room
                    if room.status == 'playing':
                        end_game(code)
                    else:
                        room_manager.delete_room(code)
                        print(f"[ROOM-] {code} (empty after disconnect)")

                elif room.status == 'playing' and len(room.players) < MIN_PLAYERS:
                    # Game was in progress but not enough players - end game, keep room, reset to lobby
                    print(f"[GAME] Not enough players, ending game but keeping room for {len(room.players)} remaining")
                    end_game(code, reset_to_lobby=True)

        # NOW delete temporary user from database (session ended)
        if is_temporary:
            delete_user_from_db(uid, username)
            print(f"[SESSION END] Deleted temp user {username} from DB")

        # Remove from memory
        del users[uid]
        print(f"[USER-] {username} removed from memory")

    if sid in sid_to_user:
        del sid_to_user[sid]


# ============================================
# WEBSOCKET: AUTH
# ============================================
@socketio.on('auth')
def on_auth(data):
    uid = data.get('user_id')
    sid = request.sid

    print(f"[AUTH] uid={uid}, sid={sid}")

    # Check memory first
    if uid not in users:
        # Try to load from DB (user might still exist from previous page load)
        loaded_user = load_user_from_db(uid)

        if loaded_user:
            users[uid] = loaded_user
            print(f"[AUTH] Restored user from DB: {loaded_user['username']}")
        else:
            print(f"[AUTH] FAILED - user {uid} not found in memory or DB")
            emit('error', {'msg': 'Invalid user'})
            return

    # Update session ID
    sid_to_user[sid] = uid
    users[uid]['sid'] = sid

    print(f"[AUTH] OK: {users[uid]['username']}")
    emit('authed', {'username': users[uid]['username']})


# ============================================
# WEBSOCKET: JOIN/LEAVE ROOM
# ============================================
@socketio.on('join')
def on_join(data):
    sid = request.sid
    uid = sid_to_user.get(sid)

    if not uid or uid not in users:
        emit('error', {'msg': 'Not authenticated'})
        return

    user = users[uid]
    code = data.get('room', '').upper()

    print(f"[JOIN] {user['username']} -> {code}")

    # Get or create room
    room = room_manager.get_room(code)
    if not room:
        room_manager.create_room(code)
        room = room_manager.get_room(code)
        print(f"[ROOM+] {code} (auto)")

    if room.status not in ['waiting', 'countdown']:
        emit('error', {'msg': 'Game in progress'})
        return

    if len(room.players) >= MAX_PLAYERS:
        emit('error', {'msg': 'Room full'})
        return

    # Add player using game_flow logic
    added = room.add_player({
        'user_id': uid,
        'username': user['username'],
        'signal_strength': user['signal']
        })

    if added:
        user['room'] = code
        join_room(code)
        print(f"[JOIN] OK - {len(room.players)} players in {code}")

    # Send room state
    player_list = room.get_player_list()
    socketio.emit('players', {'players': player_list}, room=code)
    emit('room_state', {'code': code, 'players': player_list, 'status': room.status})

@socketio.on('leave')
def on_leave(data):
    sid = request.sid
    uid = sid_to_user.get(sid)

    if not uid or uid not in users:
        return

    user = users[uid]
    code = user.get('room')

    print(f"[LEAVE] {user['username']} leaving {code}")

    if code:
        room = room_manager.get_room(code)
        if room:
            # Update signal in original_players before removing
            if hasattr(room, 'original_players'):
                for p in room.original_players:
                    if p['user_id'] == uid:
                        p['signal'] = users[uid]['signal']
                        break

            room.remove_player(uid)
            leave_room(code)

            remaining = len(room.players)
            print(f"[LEAVE] {remaining} players remaining in {code}")

            socketio.emit('player_left', {'players': room.get_player_list()}, room=code)

            # Handle different scenarios based on remaining players
            if remaining == 0:
                # Everyone left - delete room immediately
                print(f"[LEAVE] Room empty, deleting immediately")
                room_manager.delete_room(code)
                print(f"[ROOM-] {code} (empty)")
                
            elif room.status == 'playing' and remaining < MIN_PLAYERS:
                # Game was in progress but not enough players
                print(f"[LEAVE] Not enough players during game, ending and resetting")
                end_game(code, reset_to_lobby=True)

    # Clear room reference
    user['room'] = None
    print(f"[LEAVE] {user['username']} cleared room reference")


# ============================================
# WEBSOCKET: READY
# ============================================
@socketio.on('ready')
def on_ready(data):
    sid = request.sid
    uid = sid_to_user.get(sid)

    if not uid or uid not in users:
        return

    user = users[uid]
    code = user.get('room')

    if not code:
        return

    room = room_manager.get_room(code)
    if not room:
        return

    ready_state, ready_pct = room.toggle_player_ready(uid)

    print(f"[READY] {user['username']} = {ready_state} ({ready_pct:.0f}%)")

    socketio.emit('ready_update', {
        'players': room.get_player_list(),
        'ready_pct': ready_pct
        }, room=code)

    if room.can_start():
        room.start_countdown()
        print(f"[COUNTDOWN] Starting in {code}")
        socketio.emit('countdown', {'seconds': 5}, room=code)
        socketio.start_background_task(do_countdown, code)


def do_countdown(code):
    socketio.sleep(5)

    room = room_manager.get_room(code)
    if not room or room.status != 'countdown':
        return

    if room.start_game():
        # Store original player count and list for game end
        room.original_player_count = len(room.players)
        room.original_players = [
                {
                    'user_id': p.user_id,
                    'username': p.username,
                    'signal': p.signal_strength
                    }
                for p in room.players
                ]

        print(f"[GAME] Started in {code} with {room.original_player_count} players")

        socketio.emit('game_start', {
            'players': room.get_player_list(),
            'total_rounds': room.total_rounds
            }, room=code)

        socketio.sleep(3)
        start_round(code)


# ============================================
# GAME FLOW
# ============================================
def start_round(code):
    room = room_manager.get_room(code)
    if not room:
        return

    # End game if not enough players
    if len(room.players) < MIN_PLAYERS:
        print(f"[ROUND] Not enough players ({len(room.players)}), ending game and resetting")
        end_game(code, reset_to_lobby=True)
        return

    round_info = room.start_round()

    print(f"[ROUND] {round_info['round']}/{round_info['total_rounds']} - Picker: {round_info['starter']}")

    socketio.emit('round_start', {
        'round': round_info['round'],
        'total_rounds': round_info['total_rounds'],
        'picker': round_info['starter'],
        'picker_user_id': round_info['starter_user_id'],
        'max_words': round_info['max_words'],
        'players_order': round_info['players_order'],
        'word_options': round_info['word_options']
        }, room=code)


@socketio.on('submit_words')
def on_submit_words(data):
    sid = request.sid
    uid = sid_to_user.get(sid)

    if not uid or uid not in users:
        return

    user = users[uid]
    code = user.get('room')

    if not code:
        return

    room = room_manager.get_room(code)
    if not room:
        return

    words = data.get('words', [])

    message = room.submit_words(uid, words)

    if message:
        print(f"[WORDS] {user['username']}: '{message}'")

        socketio.emit('words_submitted', {
            'picker': user['username'],
            'message': message
            }, room=code)

        socketio.sleep(1)
        next_turn(code)


def next_turn(code):
    room = room_manager.get_room(code)
    if not room:
        return

    if room.is_round_complete():
        print(f"[TURN] Round complete!")
        end_round(code)
        return

    turn_info = room.get_turn_info()
    if not turn_info:
        print(f"[TURN] No turn info, round might be complete")
        end_round(code)
        return

    player_uid = turn_info['user_id']
    player_name = turn_info['username']
    player_signal = turn_info['signal']
    mutated_msg = turn_info['message']

    print(f"[TURN] {player_name} (signal:{player_signal}%)")
    print(f"[TURN] Mutated: '{mutated_msg}'")

    player_sid = users.get(player_uid, {}).get('sid')

    if not player_sid:
        print(f"[TURN] WARNING: {player_name} not connected, skipping")
        result = room.submit_typing(player_uid, turn_info['original'])
        socketio.sleep(0.5)
        next_turn(code)
        return

    # Tell others who is typing
    for p in room.get_player_list():
        if p['user_id'] != player_uid:
            other_sid = users.get(p['user_id'], {}).get('sid')
            if other_sid:
                socketio.emit('player_typing', {
                    'username': player_name,
                    'time': 15
                    }, room=other_sid)

    # Send turn to typing player
    socketio.sleep(0.1)
    socketio.emit('your_turn', {
        'message': mutated_msg,
        'original': turn_info['original'],
        'signal': player_signal,
        'time': 15
        }, room=player_sid)

    print(f"[TURN] Sent your_turn to {player_name}")


@socketio.on('submit_typing')
def on_submit_typing(data):
    sid = request.sid
    uid = sid_to_user.get(sid)

    if not uid or uid not in users:
        return

    user = users[uid]
    code = user.get('room')

    if not code:
        return

    room = room_manager.get_room(code)
    if not room:
        return

    typed = data.get('message', '')

    print(f"[TYPED] {user['username']}: '{typed}'")

    result = room.submit_typing(uid, typed)

    if result:
        player = room.get_player(uid)
        if player and uid in users:
            users[uid]['signal'] = player.signal_strength

        print(f"[TYPED] Accuracy: {result['accuracy']}%, Signal: {result['signal_change']:+d} -> {result['new_signal']}")

        socketio.emit('player_done', {'username': user['username']}, room=code)

        socketio.sleep(1)
        next_turn(code)


def end_round(code):
    room = room_manager.get_room(code)
    if not room:
        return

    round_data = room.end_round()

    if round_data:
        print(f"[ROUND END] '{round_data['original']}' -> '{round_data['final']}'")

        socketio.emit('round_end', {
            'round_data': round_data,
            'players': room.get_player_list()
            }, room=code)


# ============================================
# VOTING
# ============================================
@socketio.on('vote')
def on_vote(data):
    sid = request.sid
    uid = sid_to_user.get(sid)

    if not uid or uid not in users:
        return

    user = users[uid]
    code = user.get('room')

    if not code:
        return

    room = room_manager.get_room(code)
    if not room:
        return

    vote = data.get('vote', 'yes')

    print(f"[VOTE] {user['username']}: {vote}")

    # Record vote FIRST (before any player removal)
    room.add_vote(uid, vote)

    if vote == 'no':
        # Update signal in original_players before removing
        if hasattr(room, 'original_players'):
            for p in room.original_players:
                if p['user_id'] == uid:
                    p['signal'] = users[uid]['signal']
                    break

        # Remove from room but DON'T delete user from DB
        room.remove_player(uid)
        leave_room(code)
        user['room'] = None

        print(f"[VOTE] {user['username']} left room (still in session)")

        # Send player back to lobby
        emit('left_game', {'message': 'You left the game'})

        socketio.emit('player_left', {'players': room.get_player_list()}, room=code)

        # Check scenarios
        if not room.players:
            # Everyone left - end game completely
            print(f"[VOTE] Room empty, ending game")
            end_game(code)
            return

        elif len(room.players) < MIN_PLAYERS:
            # Not enough players to continue - end game, reset to lobby
            print(f"[VOTE] Not enough players, ending game and resetting room")
            end_game(code, reset_to_lobby=True)
            return

        # Check if all REMAINING players have voted
        if check_remaining_votes(room):
            print(f"[VOTE] All remaining players voted!")
            socketio.sleep(1)
            proceed_after_votes(code, room)

        return

    # Player voted "yes" - send update
    print(f"[VOTE] Recorded yes vote from {user['username']}")

    # Count current votes
    yes_count, no_count, voted_count = count_current_votes(room)

    socketio.emit('vote_update', {
        'votes': voted_count,
        'total': len(room.players)
        }, room=code)

    # Check if all REMAINING players have voted
    if check_remaining_votes(room):
        print(f"[VOTE] All remaining players voted!")
        proceed_after_votes(code, room)


def check_remaining_votes(room):
    """Check if all remaining players in the room have voted."""
    if not room.active_round:
        return True

    if len(room.players) == 0:
        return True

    # Check if every remaining player has voted
    for player in room.players:
        if player.user_id not in room.active_round.voted_players:
            return False

    return True


def count_current_votes(room):
    """Count votes from players still in room."""
    if not room.active_round:
        return 0, 0, 0

    yes_count = room.active_round.votes.get('yes', 0)
    no_count = room.active_round.votes.get('no', 0)
    voted_count = 0

    for player in room.players:
        if player.user_id in room.active_round.voted_players:
            voted_count += 1

    return yes_count, no_count, voted_count

def proceed_after_votes(code, room):
    """Handle game progression after all votes are in."""
    print(f"[VOTE] Proceeding - Round {room.current_round}/{room.total_rounds}")
    print(f"[VOTE] Players remaining: {len(room.players)}")

    # Reset votes for next round
    if room.active_round:
        room.active_round.voted_players = set()
        room.active_round.votes = {'yes': 0, 'no': 0}

    # Check scenarios
    if not room.players:
        print(f"[VOTE] Room empty, ending game")
        end_game(code)
        return

    if len(room.players) < MIN_PLAYERS:
        print(f"[VOTE] Not enough players ({len(room.players)} < {MIN_PLAYERS}), ending game")
        end_game(code, reset_to_lobby=True)
        return

    # REMOVED: No round limit check! Game continues FOREVER until players leave!
    # Just start the next round
    print(f"[VOTE] Starting next round (round {room.current_round + 1})")
    socketio.sleep(2)
    start_round(code)

# ============================================
# GAME END
# ============================================
def end_game(code, reset_to_lobby=False):
    """
    End the game.

    Args:
        code: Room code
        reset_to_lobby: If True, keep room alive and reset to waiting state for remaining players
    """
    room = room_manager.get_room(code)
    if not room:
        print(f"[GAME END] Room {code} not found")
        return

    # PREVENT DOUBLE-ENDING
    if room.status == 'finished':
        print(f"[GAME END] {code} already finished, skipping duplicate call")
        return

    print(f"[GAME END] ===== ENDING GAME =====")
    print(f"[GAME END] Code: {code}")
    print(f"[GAME END] Reset to lobby: {reset_to_lobby}")
    print(f"[GAME END] Players remaining: {len(room.players)}")

    # Mark as finished IMMEDIATELY to prevent race conditions
    room.status = 'finished'

    # Use original player count
    num_players = getattr(room, 'original_player_count', len(room.players))

    final_results = room.end_game()

    # Build full rankings from original players
    if hasattr(room, 'original_players'):
        # Get current signals for players still in game
        current_signals = {}
        for p in room.players:
            current_signals[p.user_id] = p.signal_strength

        # Build rankings from all original players
        rankings = []
        player_ids = []
        for p in room.original_players:
            signal = current_signals.get(p['user_id'], p['signal'])
            rankings.append({
                'user_id': p['user_id'],
                'username': p['username'],
                'signal': signal
            })
            player_ids.append(p['user_id'])

        rankings.sort(key=lambda x: x['signal'], reverse=True)

        for i, r in enumerate(rankings):
            r['rank'] = i + 1
    else:
        rankings = final_results['rankings']
        player_ids = [r['user_id'] for r in rankings]

    # Save signals to user memory
    for r in rankings:
        uid = r['user_id']
        if uid in users:
            users[uid]['signal'] = r['signal']
            print(f"[SIGNAL] {r['username']} saved: {r['signal']}%")

    print(f"[GAME END] Final rankings for {num_players} players:")
    for r in rankings:
        print(f"  #{r['rank']} {r['username']}: {r['signal']}%")

    # Save to database
    game_data = {
        'room_code': code,
        'num_players': num_players,
        'rounds': room.rounds,
        'player_results': rankings,
        'player_ids': player_ids
    }

    game_id = save_game_to_db(game_data)
    print(f"[GAME END] Saved to DB with ID: {game_id}")

    # Store game_id for session tracking
    if game_id and hasattr(room, 'original_players'):
        for p in room.original_players:
            uid = p['user_id']
            if uid in users:
                if 'session_games' not in users[uid]:
                    users[uid]['session_games'] = []
                users[uid]['session_games'].append(game_id)

    # Send game_end event to all remaining players
    socketio.emit('game_end', {
        'rankings': rankings,
        'rounds': room.rounds,
        'num_players': num_players,
        'game_id': game_id
    }, room=code)

    if reset_to_lobby:
        # Keep room alive, reset to waiting state
        print(f"[RESET] Resetting room {code} to waiting state")

        socketio.sleep(5)  # Show results for 5 seconds

        # Reset room state
        room.status = 'waiting'
        room.current_round = 0
        room.total_rounds = 0
        room.rounds = []
        room.active_round = None
        room.started_at = None
        room.ended_at = None

        # Reset all remaining players
        for p in room.players:
            p.ready = False
            p.reset_for_round()

        # Clear original_players tracking
        if hasattr(room, 'original_players'):
            delattr(room, 'original_players')
        if hasattr(room, 'original_player_count'):
            delattr(room, 'original_player_count')

        # Send reset signal to remaining players
        socketio.emit('room_reset', {
            'code': code,
            'players': room.get_player_list(),
            'message': 'Game ended. Room reset to lobby.'
        }, room=code)

        print(f"[ROOM] {code} reset to waiting state with {len(room.players)} players")

    else:
        # Delete room completely
        print(f"[GAME END] Deleting room {code}")
        
        # Clear room references for any remaining players
        for p in room.get_player_list():
            uid = p['user_id']
            if uid in users:
                users[uid]['room'] = None

        # Delete room after short delay
        socketio.start_background_task(delete_room_delayed, code)


def delete_room_delayed(code):
    """Delete room after a short delay."""
    socketio.sleep(2)
    deleted = room_manager.delete_room(code)
    if deleted:
        print(f"[ROOM-] {code} (deleted)")
    else:
        print(f"[ROOM-] {code} (already deleted)")
# ============================================
# STATIC FILES
# ============================================
@app.route('/')
def index():
    return app.send_static_file('index.html')


@app.route('/<path:path>')
def static_files(path):
    try:
        return app.send_static_file(path)
    except:
        return app.send_static_file('index.html')




def cleanup_orphaned_rooms():
    """Background task to cleanup empty rooms every 5 minutes."""
    while True:
        socketio.sleep(300)  # 5 minutes
        
        print("[CLEANUP] Checking for orphaned rooms...")
        
        # Find empty rooms
        empty_rooms = []
        for code, room in list(room_manager.rooms.items()):
            if len(room.players) == 0:
                empty_rooms.append(code)
        
        # Delete them
        for code in empty_rooms:
            room_manager.delete_room(code)
            print(f"[CLEANUP] Deleted empty room {code}")
        
        if empty_rooms:
            print(f"[CLEANUP] Removed {len(empty_rooms)} empty rooms")
        else:
            print(f"[CLEANUP] No orphaned rooms found")
# ============================================
# START SERVER
# ============================================
if __name__ == '__main__':
    print("=" * 50)
    print("WHISPERCHAIN MULTIPLAYER SERVER")
    print("=" * 50)
    print(f"Starting Signal: {STARTING_SIGNAL}%")
    print(f"Ready Threshold: {READY_THRESHOLD}%")
    print(f"Max Players: {MAX_PLAYERS}")
    print("=" * 50)

    init_db()
    cleanup_temp_users()

    # Start background cleanup task
    socketio.start_background_task(cleanup_orphaned_rooms)

    port = int(os.environ.get('PORT', 5000))
    print(f"URL: http://localhost:{port}")
    print("=" * 50)

    socketio.run(
        app,
        host='0.0.0.0',
        port=port,
        debug=config.DEBUG,
        allow_unsafe_werkzeug=True
    )
