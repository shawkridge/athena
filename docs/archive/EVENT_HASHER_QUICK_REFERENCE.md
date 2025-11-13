# EventHasher Quick Reference

## Import

```python
from athena.episodic import EventHasher, compute_event_hash
```

## Basic Usage

```python
# Create hasher
hasher = EventHasher()

# Compute hash
hash_value = hasher.compute_hash(event)

# Or use convenience function
hash_value = compute_event_hash(event)
```

## Excluded Fields (Don't Affect Hash)

- `id` - Database-assigned
- `consolidation_status` - Lifecycle state
- `consolidated_at` - Consolidation timestamp

## Example Hash Values

```
Basic event:         cd44c54870f30613086be761e70860c4b9523b18bed6becd64f1b8843ed68597
Code-aware event:    96e9ae8c5a0247c5e70864e4c628d28b523fdc80ac54d34b66e3b8c334b919e3
Test event:          9ce148a0d7fc1259352d8a219daa9ba849944fccb98596b03094e735ad89718a
Error event:         3adebc6a34ac88535dfbdfa3ddcb5bf225a980e6965f272864e1ca317c1391ba
```

## Deduplication Pattern

```python
# Compute hash
content_hash = hasher.compute_hash(event)

# Check for duplicate
existing = store.get_event_by_hash(content_hash)
if existing:
    return {"status": "duplicate", "event_id": existing.id}

# Store new event
event_id = store.record_event(event)
```

## Properties

- **Algorithm**: SHA256
- **Output**: 64-character hex string
- **Performance**: ~0.15ms per event
- **Collision rate**: Astronomically low (2^-128)

## Test

```bash
pytest tests/unit/test_episodic_hashing.py -v
# 35 passed in 0.35s
```
