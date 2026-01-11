"""Analyze signal patterns to identify churning source."""
import json
from collections import Counter
from pathlib import Path

signals_file = Path("data/signals.jsonl")
signals = []

with open(signals_file) as f:
    for line in f:
        signals.append(json.loads(line))

print(f"Total signals: {len(signals)}\n")

# Check for consecutive same-side signals
transitions = []
consecutive_same = 0

for i in range(1, len(signals)):
    prev_side = signals[i-1]['side'].upper()
    curr_side = signals[i]['side'].upper()
    transition = f"{prev_side} -> {curr_side}"
    transitions.append(transition)
    
    if prev_side == curr_side:
        consecutive_same += 1
        # Show first 5 examples
        if consecutive_same <= 5:
            print(f"❌ Consecutive {prev_side}: {signals[i-1]['timestamp']} then {signals[i]['timestamp']}")

print(f"\nTransition patterns:")
for pattern, count in Counter(transitions).most_common():
    print(f"  {pattern}: {count}")

print(f"\nConsecutive same-side signals: {consecutive_same} out of {len(signals)-1} transitions")
print(f"Perfect alternation: {consecutive_same == 0}")

if consecutive_same > 0:
    print(f"\n⚠️  Signal generator is producing consecutive {consecutive_same} same-side signals!")
    print("This is the root cause of potential position size doubling/halving.")
else:
    print("\n✅ Signals alternate perfectly - no generator issue")
