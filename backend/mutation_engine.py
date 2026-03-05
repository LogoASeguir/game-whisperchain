# mutation_engine.py
"""
WhisperChain Mutation Engine
Handles message mutation, accuracy calculation, and signal updates.

MECHANICS:
- Signal Strength (SS) determines how many letters are HIDDEN
- Formula: hidden_percent = 100 - signal_strength (minimum 10% always visible)
- Accuracy is ALWAYS compared against ORIGINAL message
- Team game: if message degrades, everyone suffers

SCORING:
- 100% accuracy → +10% SS
- 90-99% → +5%
- 85-89% → +4%
- 80-84% → +3%
- 65-79% → +2%
- 50-64% → +1%
- 35-49% → -1%
- 20-34% → -2%
- 10-19% → -3%
- 1-9% → -4%
- 0% → -5%

BOUNDS:
- SS hits 0% or 100% → reset to 50%
- Minimum SS: 10%
- Maximum SS: 99%
"""

import random


# ============================================
# CONSTANTS
# ============================================
MIN_SIGNAL = 10
MAX_SIGNAL = 99
RESET_SIGNAL = 50
MIN_VISIBLE_PERCENT = 10  # Always show at least 10% of letters


# ============================================
# MUTATION FUNCTIONS
# ============================================
def mutate_word(word, signal_strength):
    """
    Mutate a word based on signal strength.
    
    Higher signal = MORE letters visible
    Lower signal = FEWER letters visible
    
    Formula: visible_percent = signal_strength (minimum 10%)
    """
    if not word:
        return word
    
    letters = list(word)
    word_length = len(letters)
    
    # Calculate how many letters to SHOW (not hide)
    # Signal strength directly correlates to visibility
    visible_percent = max(MIN_VISIBLE_PERCENT, signal_strength)
    num_to_show = max(1, int(word_length * visible_percent / 100))
    
    # Ensure we don't try to show more letters than exist
    num_to_show = min(num_to_show, word_length)
    
    # Randomly select which positions to KEEP visible
    all_positions = list(range(word_length))
    visible_positions = set(random.sample(all_positions, num_to_show))
    
    # Build result: show letter if in visible_positions, else underscore
    result = []
    for pos in range(word_length):
        if pos in visible_positions:
            result.append(letters[pos])
        else:
            result.append("_")
    
    return ''.join(result)


def mutate_message(message, signal_strength):
    """
    Mutate entire message based on signal strength.
    
    Each word is mutated independently.
    Spaces are preserved.
    """
    if not message:
        return message
    
    words = message.split(' ')
    
    mutated_words = []
    for word in words:
        if word:  # Skip empty strings from multiple spaces
            mutated = mutate_word(word, signal_strength)
            mutated_words.append(mutated)
        else:
            mutated_words.append(word)
    
    return ' '.join(mutated_words)


# ============================================
# ACCURACY CALCULATION
# ============================================
def calculate_accuracy(original, typed):
    """
    Compare typed message against ORIGINAL message.
    
    Returns accuracy percentage (0-100).
    Only compares letter positions, spaces are handled separately.
    Underscores in typed message count as wrong.
    """
    if not original:
        return 100.0 if not typed else 0.0
    
    # Normalize: compare character by character
    orig_chars = list(original.lower())
    typed_chars = list(typed.lower())
    
    # Handle length mismatch
    if len(orig_chars) != len(typed_chars):
        # Calculate based on shorter length, penalize for mismatch
        min_len = min(len(orig_chars), len(typed_chars))
        max_len = max(len(orig_chars), len(typed_chars))
        length_penalty = min_len / max_len if max_len > 0 else 0
    else:
        length_penalty = 1.0
        min_len = len(orig_chars)
    
    if min_len == 0:
        return 0.0
    
    correct = 0
    total = 0
    
    for i in range(min_len):
        orig_char = orig_chars[i]
        typed_char = typed_chars[i]
        
        # Skip spaces in counting
        if orig_char == ' ':
            continue
        
        total += 1
        
        # Underscore = wrong, otherwise compare
        if typed_char != '_' and orig_char == typed_char:
            correct += 1
    
    if total == 0:
        return 100.0
    
    accuracy = (correct / total) * 100 * length_penalty
    return round(accuracy, 1)


# ============================================
# SIGNAL STRENGTH UPDATES
# ============================================
def calculate_signal_change(accuracy):
    """
    Calculate signal change based on accuracy.
    
    REWARDS (positive):
    - 100% → +10
    - 90-99% → +5
    - 85-89% → +4
    - 80-84% → +3
    - 65-79% → +2
    - 50-64% → +1
    
    PENALTIES (negative - mirror of rewards):
    - 35-49% → -1
    - 20-34% → -2
    - 10-19% → -3
    - 1-9% → -4
    - 0% → -5
    """
    if accuracy >= 100:
        return 10
    elif accuracy >= 90:
        return 5
    elif accuracy >= 85:
        return 4
    elif accuracy >= 80:
        return 3
    elif accuracy >= 65:
        return 2
    elif accuracy >= 50:
        return 1
    elif accuracy >= 35:
        return -1
    elif accuracy >= 20:
        return -2
    elif accuracy >= 10:
        return -3
    elif accuracy >= 1:
        return -4
    else:
        return -5


def check_signal_bounds(signal_strength):
    """
    Check and reset signal if it hits bounds.
    
    - 0% or below → reset to 50%
    - 100% or above → reset to 50%
    - Otherwise clamp between MIN_SIGNAL and MAX_SIGNAL
    """
    if signal_strength <= 0 or signal_strength >= 100:
        return RESET_SIGNAL
    
    return max(MIN_SIGNAL, min(MAX_SIGNAL, signal_strength))


def update_signal_strength(current_signal, accuracy):
    """
    Update signal strength based on accuracy.
    
    1. Calculate change from accuracy
    2. Apply change
    3. Check bounds (reset if 0% or 100%)
    """
    change = calculate_signal_change(accuracy)
    new_signal = current_signal + change
    
    # Apply bounds check (resets to 50 if hits 0 or 100)
    new_signal = check_signal_bounds(new_signal)
    
    return new_signal


# ============================================
# LEGACY FUNCTION (for compatibility)
# ============================================
def check_signal(signal_strength):
    """Legacy function - use check_signal_bounds instead."""
    return check_signal_bounds(signal_strength)


# ============================================
# TESTS
# ============================================
if __name__ == "__main__":
    print("=" * 60)
    print("MUTATION ENGINE TESTS - NEW MECHANICS")
    print("=" * 60)
    
    print("\n--- Word Mutation (SS = visibility %) ---")
    test_word = "whisperchain"
    for ss in [99, 80, 65, 50, 35, 20, 10]:
        mutated = mutate_word(test_word, ss)
        visible = sum(1 for c in mutated if c != '_')
        print(f"  SS {ss:2d}%: '{mutated}' ({visible}/{len(test_word)} visible)")
    
    print("\n--- Message Mutation ---")
    test_msg = "ninja penguin wizard"
    for ss in [90, 70, 50, 30, 10]:
        mutated = mutate_message(test_msg, ss)
        print(f"  SS {ss:2d}%: '{mutated}'")
    
    print("\n--- Accuracy Calculation (vs ORIGINAL) ---")
    original = "ninja taco"
    test_cases = [
        ("ninja taco", "Perfect match"),
        ("ninja tac_", "One underscore"),
        ("ninja _a_o", "Multiple underscores"),
        ("ninjx txco", "Wrong letters"),
        ("_____ ____", "All underscores"),
        ("ninja tacos", "Extra letter"),
        ("ninja tac", "Missing letter"),
    ]
    
    for typed, desc in test_cases:
        acc = calculate_accuracy(original, typed)
        change = calculate_signal_change(acc)
        sign = "+" if change >= 0 else ""
        print(f"  '{typed}' - {desc}")
        print(f"    Accuracy: {acc}% → Signal {sign}{change}")
    
    print("\n--- Signal Change Thresholds ---")
    thresholds = [100, 95, 90, 85, 80, 70, 65, 55, 50, 40, 35, 25, 20, 15, 10, 5, 0]
    for acc in thresholds:
        change = calculate_signal_change(acc)
        sign = "+" if change >= 0 else ""
        print(f"  {acc:3d}% accuracy → {sign}{change} signal")
    
    print("\n--- Signal Bounds (reset at 0% or 100%) ---")
    test_signals = [5, 10, 50, 95, 99, 100, 105, 0, -5]
    for sig in test_signals:
        result = check_signal_bounds(sig)
        print(f"  {sig:3d}% → {result}%", "(RESET)" if result == 50 and sig != 50 else "")
    
    print("\n--- Full Signal Update ---")
    scenarios = [
        (50, 100, "Perfect from 50%"),
        (50, 75, "Good from 50%"),
        (50, 55, "Okay from 50%"),
        (50, 40, "Poor from 50%"),
        (50, 10, "Bad from 50%"),
        (95, 100, "Perfect from 95% (will reset!)"),
        (15, 0, "Zero from 15% (will reset!)"),
        (12, 30, "Poor from 12%"),
    ]
    
    for current, accuracy, desc in scenarios:
        change = calculate_signal_change(accuracy)
        new = update_signal_strength(current, accuracy)
        sign = "+" if change >= 0 else ""
        reset_note = " (RESET!)" if new == 50 and current != 50 else ""
        print(f"  {desc}")
        print(f"    {current}% {sign}{change} → {new}%{reset_note}")
    
    print("\n--- Chain Simulation (Team Game) ---")
    original = "dragon wizard"
    signals = [70, 55, 40]  # Three players with different signals
    
    print(f"  Original: '{original}'")
    print()
    
    current_message = original
    for i, signal in enumerate(signals):
        player = f"Player {i+1}"
        
        # Player sees mutated version
        mutated = mutate_message(current_message, signal)
        
        # Simulate player typing (keeping what they see + guessing blanks)
        # For simulation, just use the mutated version as their input
        typed = mutated.replace('_', 'x')  # Simulate wrong guesses for blanks
        
        # Accuracy is against ORIGINAL
        accuracy = calculate_accuracy(original, typed)
        change = calculate_signal_change(accuracy)
        new_signal = update_signal_strength(signal, accuracy)
        
        sign = "+" if change >= 0 else ""
        print(f"  {player} (SS: {signal}%)")
        print(f"    Sees:    '{mutated}'")
        print(f"    Types:   '{typed}'")
        print(f"    vs Original: {accuracy}% → {sign}{change} → New SS: {new_signal}%")
        print()
        
        # Message degrades for next player
        current_message = typed
    
    print("=" * 60)
    print("TESTS COMPLETE")
    print("=" * 60)
