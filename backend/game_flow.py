"""
WhisperChain Game Flow Engine
Handles all game logic, room management, and player turns.
"""

import random
import string
from datetime import datetime
from mutation_engine import mutate_message, calculate_accuracy, update_signal_strength


# ============================================
# CONSTANTS
# ============================================
WORD_BANK = [
        "ninja", "taco", "penguin", "robot", "wizard", "pizza",
        "dragon", "banana", "volcano", "unicorn", "mermaid", "rocket",
        "zombie", "pirate", "rainbow", "tornado", "hamster", "disco",
        "gorilla", "waffle", "spaceship", "dinosaur", "octopus", "burrito",
        "cactus", "dolphin", "elephant", "flamingo", "giraffe", "hedgehog",
        "iguana", "jellyfish", "kangaroo", "leopard", "mushroom", "narwhal",
        "ostrich", "panda", "quokka", "raccoon", "squirrel", "turtle",
        "umbrella", "vampire", "werewolf", "xylophone", "yeti", "zebra"
        ]

MIN_PLAYERS = 2
MAX_PLAYERS = 10
READY_THRESHOLD = 60
STARTING_SIGNAL = 50
MIN_SIGNAL = 10
MAX_SIGNAL = 99


# ============================================
# ROOM CODE UTILITIES
# ============================================
def generate_room_code():
    """
    Generate unique room code: 2 digits + 1 letter.
    Examples: 42X, 17B, 88Z
    """
    numbers = str(random.randint(10, 99))
    letter = random.choice(string.ascii_uppercase)
    return numbers + letter


def validate_room_code(code):
    """
    Validate room code format.
    Must be 2 digits + 1 uppercase letter.
    """
    if not code or len(code) != 3:
        return False
    if not code[:2].isdigit():
        return False
    if not code[2].isalpha():
        return False
    return True


# ============================================
# WORD UTILITIES
# ============================================
def get_random_words(count=12):
    """Get random words for picking phase."""
    shuffled = WORD_BANK.copy()
    random.shuffle(shuffled)
    return shuffled[:count]


def get_max_words_for_round(round_number):
    """
    Calculate max words for a round.
    Round 1-2: 2 words
    Round 3-4: 3 words
    Round 5-6: 4 words
    etc. (max 10)
    """
    base = 2
    bonus = (round_number - 1) // 2
    return min(base + bonus, 10)


# ============================================
# PLAYER CLASS
# ============================================
class Player:
    """Represents a player in the game."""

    def __init__(self, user_id, username, signal_strength=STARTING_SIGNAL):
        self.user_id = user_id
        self.username = username
        self.signal_strength = signal_strength
        self.ready = False
        self.has_submitted = False
        self.current_answer = None
        self.round_score = 0

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
                'user_id': self.user_id,
                'username': self.username,
                'signal': self.signal_strength,
                'signal_strength': self.signal_strength,
                'ready': self.ready
                }

    def reset_for_round(self):
        """Reset player state for new round."""
        self.has_submitted = False
        self.current_answer = None
        self.round_score = 0

    def update_signal(self, change):
        """Update signal strength with bounds checking."""
        self.signal_strength = max(MIN_SIGNAL, min(MAX_SIGNAL, self.signal_strength + change))
        self.round_score = change


# ============================================
# CHAIN ENTRY CLASS
# ============================================
class ChainEntry:
    """Represents one step in the message chain."""

    def __init__(self, player, received_message, typed_message, is_picker=False):
        self.player = player
        self.received_message = received_message
        self.typed_message = typed_message
        self.is_picker = is_picker
        self.accuracy = 100.0 if is_picker else 0.0
        self.signal_change = 0
        self.new_signal = player.signal_strength

    def calculate_results(self, original_message, blank_positions=None):
        """Calculate accuracy and signal change."""
        if self.is_picker:
            self.accuracy = 100.0
            self.signal_change = 0
            return

        # FIX: Calculate accuracy only on blank positions
        self.accuracy = calculate_accuracy(original_message, self.typed_message, blank_positions)

        # Calculate signal change
        old_signal = self.player.signal_strength
        self.new_signal = update_signal_strength(old_signal, self.accuracy)
        self.signal_change = self.new_signal - old_signal

        # Update player
        self.player.update_signal(self.signal_change)

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
                'player': self.player.username,
                'user_id': self.player.user_id,
                'message': self.typed_message,
                'received': self.received_message,
                'typed': self.typed_message,
                'is_picker': self.is_picker,
                'accuracy': round(self.accuracy, 1),
                'signal_change': self.signal_change,
                'signal': self.new_signal,
                'new_signal': self.new_signal
                }


# ============================================
# ROUND CLASS
# ============================================
class Round:
    """Manages a single round of the game."""

    def __init__(self, round_number, players, picker_index):
        self.round_number = round_number
        self.players = players
        self.picker_index = picker_index
        self.max_words = get_max_words_for_round(round_number)

        self.original_message = ""
        self.current_message = ""
        self.current_turn = 0
        self.chain = []
        self.status = 'picking'

        self.votes = {'yes': 0, 'no': 0}
        self.voted_players = set()

    @property
    def picker(self):
        """Get the picker player for this round."""
        return self.players[0]

    @property
    def current_player(self):
        """Get the current player."""
        if self.current_turn < len(self.players):
            return self.players[self.current_turn]
        return None

    def get_players_order(self):
        """Get list of player usernames in order."""
        return [p.username for p in self.players]

    def submit_words(self, words):
        """
        Picker submits chosen words.
        Returns the message string.
        """
        if self.status != 'picking':
            return None

        message = ' '.join(words)
        self.original_message = message
        self.current_message = message

        # Add picker to chain
        entry = ChainEntry(
                player=self.picker,
                received_message=message,
                typed_message=message,
                is_picker=True
                )
        self.chain.append(entry)

        # Move to next player
        self.current_turn = 1
        self.status = 'passing'

        return message

    def get_message_for_player(self, player):
        """
        Get the mutated message that a player should see.
        Based on their signal strength.
        """
        return mutate_message(self.current_message, player.signal_strength)
    def submit_typing(self, player, typed_message):
        """
        Player submits their typed message.
        Returns dict with results or None if not their turn.
        """
        if self.status != 'passing':
            return None

        if self.current_player != player:
            return None

        # What they received (mutated from current_message - for display only)
        received = self.get_message_for_player(player)

        # Get blank positions by comparing original vs received
        # A position is "blank" if received has '_' at that position
        blank_positions = set()
        for i, char in enumerate(received):
            if char == '_':
                blank_positions.add(i)

        # Create chain entry
        entry = ChainEntry(
                player=player,
                received_message=received,
                typed_message=typed_message,
                is_picker=False
                )
        # Calculate accuracy: compare typed vs ORIGINAL, only at blank positions
        entry.calculate_results(self.original_message, blank_positions)
        self.chain.append(entry)

        # Update current message for next player
        self.current_message = typed_message

        # Move to next player
        self.current_turn += 1

        # Check if round is complete
        if self.current_turn >= len(self.players):
            self.status = 'revealing'

        return entry.to_dict()
    def is_complete(self):
        """Check if all players have had their turn."""
        return self.current_turn >= len(self.players)

    def get_waiting_players(self):
        """Get list of players who haven't submitted yet."""
        if self.current_turn >= len(self.players):
            return []
        return [p.username for p in self.players[self.current_turn:]]

    def add_vote(self, player, vote):
        """
        Add a player's vote.
        Returns True if all players have voted.
        """
        if player.user_id in self.voted_players:
            return len(self.voted_players) >= len(self.players)

        self.voted_players.add(player.user_id)

        if vote == 'yes':
            self.votes['yes'] += 1
        else:
            self.votes['no'] += 1

        return len(self.voted_players) >= len(self.players)

    def should_continue(self):
        """Check if players voted to continue."""
        total = self.votes['yes'] + self.votes['no']
        if total == 0:
            return True
        return (self.votes['no'] / total) < 0.5

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
                'round': self.round_number,
                'original': self.original_message,
                'final': self.current_message,
                'max_words': self.max_words,
                'chain': [entry.to_dict() for entry in self.chain],
                'votes': self.votes.copy()
                }


# ============================================
# GAME ROOM CLASS
# ============================================
class GameRoom:
    """
    Manages a complete game room with multiple rounds.
    """

    def __init__(self, code, max_players=MAX_PLAYERS):
        self.code = code
        self.max_players = max_players
        self.players = []
        self.status = 'waiting'

        # Game state
        self.current_round = 0
        self.total_rounds = 0
        self.rounds = []
        self.active_round = None

        # Timestamps
        self.created_at = datetime.now()
        self.started_at = None
        self.ended_at = None

    # ==================
    # PLAYER MANAGEMENT
    # ==================
    def add_player(self, player_data):
        """
        Add a player to the room.
        player_data: dict with user_id, username, signal_strength
        Returns: True if added, False if room full or game started
        """
        if len(self.players) >= self.max_players:
            return False

        if self.status not in ('waiting', 'countdown'):
            return False

        # Check if already in room
        for p in self.players:
            if p.user_id == player_data['user_id']:
                return False

        player = Player(
                user_id=player_data['user_id'],
                username=player_data['username'],
                signal_strength=player_data.get('signal_strength', STARTING_SIGNAL)
                )

        self.players.append(player)
        return True

    def remove_player(self, user_id):
        """Remove a player from the room."""
        self.players = [p for p in self.players if p.user_id != user_id]
        return True

    def get_player(self, user_id):
        """Get a player by user_id."""
        for p in self.players:
            if p.user_id == user_id:
                return p
        return None

    def get_player_list(self):
        """Get list of player dicts for sending to clients."""
        return [p.to_dict() for p in self.players]

    # ==================
    # READY SYSTEM
    # ==================
    def toggle_player_ready(self, user_id):
        """
        Toggle a player's ready state.
        Returns: (ready_state, ready_percent)
        """
        player = self.get_player(user_id)
        if not player:
            return None, 0

        player.ready = not player.ready
        return player.ready, self.get_ready_percent()

    def get_ready_percent(self):
        """Calculate percentage of ready players."""
        if not self.players:
            return 0
        ready_count = sum(1 for p in self.players if p.ready)
        return (ready_count / len(self.players)) * 100

    def can_start(self):
        """Check if game can start (60%+ ready, 2+ players)."""
        return (
                len(self.players) >= MIN_PLAYERS and
                self.get_ready_percent() >= READY_THRESHOLD and
                self.status == 'waiting'
                )

    def start_countdown(self):
        """Start the countdown to game start."""
        if not self.can_start():
            return False
        self.status = 'countdown'
        return True

    # ==================
    # GAME FLOW
    # ==================
    def start_game(self):
        """
        Start the game.
        Returns: True if started, False if can't start
        """
        if len(self.players) < MIN_PLAYERS:
            return False

        self.status = 'playing'
        self.started_at = datetime.now()
        self.total_rounds = len(self.players)
        self.current_round = 0

        return True

    def start_round(self):
        """
        Start a new round.
        Returns: dict with round info for clients
        """
        self.current_round += 1

        # FIX: Update total_rounds for infinite rounds
        if self.current_round > self.total_rounds:
            self.total_rounds = self.current_round

        # Reset players for new round
        for p in self.players:
            p.reset_for_round()

        # Rotate players so picker changes each round
        picker_index = (self.current_round - 1) % len(self.players)

        # Create rotated player list (picker first)
        rotated = self.players[picker_index:] + self.players[:picker_index]

        # Create new round
        self.active_round = Round(
                round_number=self.current_round,
                players=rotated,
                picker_index=picker_index
                )

        return {
                'round': self.current_round,
                'total_rounds': self.total_rounds,
                'starter': self.active_round.picker.username,
                'starter_user_id': self.active_round.picker.user_id,
                'max_words': self.active_round.max_words,
                'players_order': self.active_round.get_players_order(),
                'word_options': get_random_words(12)
                }

    def submit_words(self, user_id, words):
        """
        Picker submits their chosen words.
        Returns: message string or None if invalid
        """
        if not self.active_round:
            return None

        if self.active_round.picker.user_id != user_id:
            return None

        return self.active_round.submit_words(words)

    def get_turn_info(self):
        """
        Get current turn information.
        Returns: dict with current player info, or None if round complete
        """
        if not self.active_round:
            return None

        current = self.active_round.current_player
        if not current:
            return None

        return {
                'user_id': current.user_id,
                'username': current.username,
                'signal': current.signal_strength,
                'message': self.active_round.get_message_for_player(current),
                'original': self.active_round.current_message
                }

    def submit_typing(self, user_id, typed_message):
        """
        Player submits their typed message.
        Returns: dict with results, or None if invalid
        """
        if not self.active_round:
            return None

        player = self.get_player(user_id)
        if not player:
            return None

        return self.active_round.submit_typing(player, typed_message)

    def is_round_complete(self):
        """Check if current round is complete."""
        return self.active_round and self.active_round.is_complete()

    def end_round(self):
        """
        End the current round.
        Returns: dict with round results
        """
        if not self.active_round:
            return None

        self.active_round.status = 'voting'
        round_data = self.active_round.to_dict()
        self.rounds.append(round_data)

        return round_data

    def add_vote(self, user_id, vote):
        """
        Add a player's vote.
        Returns: (all_voted, vote_counts)
        """
        if not self.active_round:
            return False, {}

        player = self.get_player(user_id)
        if not player:
            return False, {}

        all_voted = self.active_round.add_vote(player, vote)

        return all_voted, {
                'yes': self.active_round.votes['yes'],
                'no': self.active_round.votes['no'],
                'total': len(self.players)
                }

    def should_continue(self):
        """Check if game should continue to next round."""
        if not self.active_round:
            return False

        # Check votes
        if not self.active_round.should_continue():
            return False

        # Check if more rounds
        if self.current_round >= self.total_rounds:
            return False

        return True

    def end_game(self):
        """
        End the game and calculate final rankings.
        Returns: dict with final results
        """
        self.status = 'finished'
        self.ended_at = datetime.now()

        # Sort players by signal strength
        sorted_players = sorted(
                self.players,
                key=lambda p: p.signal_strength,
                reverse=True
                )

        rankings = []
        for i, player in enumerate(sorted_players):
            rankings.append({
                'rank': i + 1,
                'user_id': player.user_id,
                'username': player.username,
                'signal': player.signal_strength,
                'signal_strength': player.signal_strength
                })

        return {
                'rankings': rankings,
                'rounds': self.rounds,
                'total_rounds': self.current_round
                }

    def get_final_results(self):
        """Get final results for database storage."""
        return {
                'room_code': self.code,
                'num_players': len(self.players),
                'rounds': self.rounds,
                'player_results': [
                    {
                        'username': p.username,
                        'signal': p.signal_strength,
                        'signal_strength': p.signal_strength
                        }
                    for p in sorted(self.players, key=lambda x: x.signal_strength, reverse=True)
                    ]
                }


# ============================================
# ROOM MANAGER
# ============================================
class RoomManager:
    """
    Manages all active game rooms.
    """

    def __init__(self, max_rooms=100):
        self.rooms = {}
        self.max_rooms = max_rooms

    def create_room(self, code=None):
        """
        Create a new room.
        Returns: room code or None if at capacity
        """
        if len(self.rooms) >= self.max_rooms:
            return None

        if not code or not validate_room_code(code):
            code = generate_room_code()
            while code in self.rooms:
                code = generate_room_code()

        if code in self.rooms:
            return None

        self.rooms[code] = GameRoom(code)
        return code

    def get_room(self, code):
        """Get a room by code."""
        return self.rooms.get(code.upper() if code else None)

    def delete_room(self, code):
        """Delete a room."""
        code = code.upper() if code else None
        if code in self.rooms:
            del self.rooms[code]
            return True
        return False

    def get_all_rooms(self):
        """Get list of all rooms for lobby display."""
        rooms_list = []
        for code, room in self.rooms.items():
            rooms_list.append({
                'code': code,
                'status': room.status,
                'players': len(room.players),
                'max_players': room.max_players
                })
        return rooms_list

    def cleanup_empty_rooms(self):
        """Remove rooms with no players."""
        empty = [code for code, room in self.rooms.items() if not room.players]
        for code in empty:
            del self.rooms[code]
        return len(empty)


# ============================================
# TESTS
# ============================================
if __name__ == "__main__":
    print("=" * 60)
    print("GAME FLOW TESTS")
    print("=" * 60)

    # Test room code
    print("\n--- Room Codes ---")
    for _ in range(5):
        code = generate_room_code()
        valid = validate_room_code(code)
        print(f"  {code} - valid: {valid}")

    # Test word generation
    print("\n--- Word Generation ---")
    words = get_random_words(6)
    print(f"  Random words: {words}")

    # Test max words per round
    print("\n--- Max Words Per Round ---")
    for r in range(1, 8):
        max_w = get_max_words_for_round(r)
        print(f"  Round {r}: {max_w} words")

    # Test game flow
    print("\n--- Full Game Simulation ---")

    manager = RoomManager()
    code = manager.create_room()
    room = manager.get_room(code)
    print(f"  Created room: {code}")

    # Add players
    room.add_player({'user_id': 1, 'username': 'Alice', 'signal_strength': 70})
    room.add_player({'user_id': 2, 'username': 'Bob', 'signal_strength': 50})
    room.add_player({'user_id': 3, 'username': 'Carol', 'signal_strength': 60})
    print(f"  Added 3 players")

    # Ready up
    room.toggle_player_ready(1)
    room.toggle_player_ready(2)
    ready_pct = room.get_ready_percent()
    print(f"  Ready: {ready_pct:.0f}%")

    room.toggle_player_ready(3)
    print(f"  Can start: {room.can_start()}")

    # Start game
    room.start_game()
    print(f"  Game started! Rounds: {room.total_rounds}")

    # Play a round
    round_info = room.start_round()
    print(f"\n  Round {round_info['round']}")
    print(f"  Picker: {round_info['starter']}")
    print(f"  Max words: {round_info['max_words']}")

    # Picker submits words
    message = room.submit_words(round_info['starter_user_id'], ['ninja', 'taco'])
    print(f"  Original: {message}")

    # Other players take turns
    while not room.is_round_complete():
        turn = room.get_turn_info()
        if turn:
            print(f"\n  {turn['username']}'s turn (signal: {turn['signal']}%)")
            print(f"    Sees: {turn['message']}")

            # Simulate typing (just echo for test)
            result = room.submit_typing(turn['user_id'], turn['message'].replace('_', 'x'))
            if result:
                print(f"    Typed: {result['typed']}")
                print(f"    Accuracy: {result['accuracy']}%")
                print(f"    Signal: {result['signal_change']:+d}")

    # End round
    round_result = room.end_round()
    print(f"\n  Round complete!")
    print(f"  Original: {round_result['original']}")
    print(f"  Final: {round_result['final']}")

    # End game
    final = room.end_game()
    print(f"\n  Game Over!")
    for r in final['rankings']:
        print(f"    #{r['rank']} {r['username']}: {r['signal']}%")

    print("\n" + "=" * 60)
    print("TESTS COMPLETE")
    print("=" * 60)
