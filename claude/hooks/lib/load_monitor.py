"""Cognitive load monitoring using 7±2 working memory model."""

from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
from pathlib import Path


@dataclass
class WorkingMemoryItem:
    """Item in working memory."""

    id: str
    content: str
    created_at: str
    last_accessed: str
    decay_rate: float  # 0.0-1.0, higher = faster decay
    importance: float  # 0.0-1.0, salience score
    active_cycles: int  # Number of times accessed


class LoadMonitor:
    """Monitor cognitive load using 7±2 working memory model."""

    # Baddeley's working memory model: 7±2 items
    OPTIMAL_CAPACITY = 7
    OPTIMAL_LOAD_RANGE = (2, 4)  # 2-4 items optimal
    CAUTION_THRESHOLD = 5  # Alert at 5/7
    AUTO_CONSOLIDATE_THRESHOLD = 6  # Auto-consolidate at 6/7
    OVERFLOW_THRESHOLD = 7  # Emergency at 7/7

    # Item decay rates (per hour)
    HIGH_DECAY_RATE = 0.5  # Fades quickly
    NORMAL_DECAY_RATE = 0.2  # Normal decay
    LOW_DECAY_RATE = 0.05  # Stays longer

    def __init__(self, memory_file: Optional[str] = None):
        """Initialize load monitor.

        Args:
            memory_file: Path to working memory state file.
                         Defaults to ~/.claude/hooks/.working-memory
        """
        if memory_file is None:
            memory_file = str(
                Path.home() / ".claude" / "hooks" / ".working-memory"
            )

        self.memory_file = Path(memory_file)
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing working memory
        self.working_memory: List[WorkingMemoryItem] = self._load_memory()

    def add_item(
        self,
        item_id: str,
        content: str,
        importance: float = 0.5,
        decay_rate: Optional[float] = None,
    ) -> None:
        """Add item to working memory.

        Args:
            item_id: Unique item identifier
            content: Item content
            importance: Importance/salience (0.0-1.0)
            decay_rate: Decay rate (if None, use NORMAL_DECAY_RATE)
        """
        if decay_rate is None:
            decay_rate = self.NORMAL_DECAY_RATE

        item = WorkingMemoryItem(
            id=item_id,
            content=content,
            created_at=datetime.utcnow().isoformat(),
            last_accessed=datetime.utcnow().isoformat(),
            decay_rate=decay_rate,
            importance=importance,
            active_cycles=0,
        )

        self.working_memory.append(item)
        self._save_memory()

    def remove_item(self, item_id: str) -> bool:
        """Remove item from working memory.

        Args:
            item_id: Item identifier

        Returns:
            True if removed, False if not found
        """
        original_len = len(self.working_memory)
        self.working_memory = [
            item for item in self.working_memory if item.id != item_id
        ]

        if len(self.working_memory) < original_len:
            self._save_memory()
            return True

        return False

    def access_item(self, item_id: str) -> bool:
        """Access an item (updates decay tracking).

        Args:
            item_id: Item identifier

        Returns:
            True if item found, False otherwise
        """
        for item in self.working_memory:
            if item.id == item_id:
                item.last_accessed = datetime.utcnow().isoformat()
                item.active_cycles += 1
                self._save_memory()
                return True

        return False

    def get_current_load(self) -> int:
        """Get current working memory load.

        Returns:
            Number of items currently in working memory
        """
        return len(self.working_memory)

    def get_load_percentage(self) -> float:
        """Get load as percentage of capacity.

        Returns:
            Percentage (0.0-1.0)
        """
        return self.get_current_load() / self.OPTIMAL_CAPACITY

    def get_load_zone(self) -> str:
        """Get current cognitive load zone.

        Returns:
            Zone name (OPTIMAL, CAUTION, NEAR_CAPACITY, OVERFLOW)
        """
        load = self.get_current_load()

        if load <= self.OPTIMAL_LOAD_RANGE[1]:
            return "OPTIMAL"
        elif load < self.CAUTION_THRESHOLD:
            return "NORMAL"
        elif load < self.AUTO_CONSOLIDATE_THRESHOLD:
            return "CAUTION"
        elif load < self.OVERFLOW_THRESHOLD:
            return "NEAR_CAPACITY"
        else:
            return "OVERFLOW"

    def get_status(self) -> Dict:
        """Get complete load status.

        Returns:
            Status dictionary with capacity, zone, and items
        """
        load = self.get_current_load()
        zone = self.get_load_zone()

        return {
            "current_load": load,
            "capacity": self.OPTIMAL_CAPACITY,
            "percentage": self.get_load_percentage(),
            "zone": zone,
            "items": [asdict(item) for item in self.working_memory],
            "should_consolidate": load >= self.AUTO_CONSOLIDATE_THRESHOLD,
        }

    def get_items_for_archiving(self) -> List[WorkingMemoryItem]:
        """Get items that should be archived due to decay.

        Items with decay > 0.3 and haven't been accessed recently
        should be consolidated into semantic memory.

        Returns:
            List of items to archive
        """
        now = datetime.utcnow()
        to_archive = []

        for item in self.working_memory:
            last_accessed = datetime.fromisoformat(item.last_accessed)
            time_since_access = (now - last_accessed).total_seconds() / 3600

            # Calculate decay score
            decay_score = item.decay_rate * time_since_access

            # Archive if decay significant and not important
            if decay_score > 0.3 and item.importance < 0.7:
                to_archive.append(item)

        return to_archive

    def consolidate(self, item_ids: List[str]) -> int:
        """Remove items from working memory (consolidate to semantic).

        Args:
            item_ids: List of item IDs to consolidate

        Returns:
            Number of items consolidated
        """
        consolidated = 0
        for item_id in item_ids:
            if self.remove_item(item_id):
                consolidated += 1

        return consolidated

    def clear(self) -> None:
        """Clear all working memory items."""
        self.working_memory = []
        self._save_memory()

    def _save_memory(self) -> None:
        """Save working memory to file."""
        data = [asdict(item) for item in self.working_memory]

        with open(self.memory_file, "w") as f:
            json.dump(data, f, indent=2)

    def _load_memory(self) -> List[WorkingMemoryItem]:
        """Load working memory from file.

        Returns:
            List of working memory items
        """
        if not self.memory_file.exists():
            return []

        try:
            with open(self.memory_file, "r") as f:
                data = json.load(f)

            return [
                WorkingMemoryItem(
                    id=item["id"],
                    content=item["content"],
                    created_at=item["created_at"],
                    last_accessed=item["last_accessed"],
                    decay_rate=item["decay_rate"],
                    importance=item["importance"],
                    active_cycles=item["active_cycles"],
                )
                for item in data
            ]

        except (json.JSONDecodeError, KeyError):
            return []
