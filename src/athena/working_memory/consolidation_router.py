"""
ML-based Consolidation Router: Intelligent routing of working memory to LTM.

Purpose:
- Automatically determine which long-term memory layer to consolidate to
- Use machine learning to improve routing decisions over time
- Provide heuristic fallbacks when ML model not trained
- Support online learning from user feedback

Target Layers:
- Semantic: Facts, concepts, general knowledge
- Episodic: Events, temporal information
- Procedural: Workflows, how-to knowledge
- Prospective: Future tasks, reminders

Features:
- Feature extraction from content
- Random Forest classifier with online learning
- Heuristic-based fallback
- Confidence scoring
- Feedback loop for continuous improvement
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json
import re
import numpy as np

from ..core.database import Database
from .models import WorkingMemoryItem, TargetLayer, ConsolidationRoute


class ConsolidationRouter:
    """
    ML-based router for consolidating working memory to appropriate layer.

    Uses Random Forest classifier trained on historical consolidation decisions
    with online learning from user feedback.
    """

    def __init__(self, db: Database | str):
        # Accept either Database instance or path string
        if isinstance(db, Database):
            self.db = db
        else:
            self.db = Database(db)
        self.model = None
        self.is_trained = False
        self.feature_names = [
            'content_length',
            'is_verbal',
            'is_spatial',
            'activation_level',
            'importance_score',
            'time_in_wm_seconds',
            'has_temporal_markers',
            'has_action_verbs',
            'has_future_markers',
            'has_question_words',
            'has_file_references'
        ]

    # ========================================================================
    # Routing Decision
    # ========================================================================

    def route_item(self, project_id: int, item_id: int, use_ml: bool = True) -> dict:
        """Route working memory item to appropriate LTM layer."""
        # Get item
        with self.db.conn:
            row = self.db.conn.execute("""
                SELECT * FROM working_memory WHERE id = ?
            """, (item_id,)).fetchone()
            if not row:
                raise ValueError(f"Item {item_id} not found")

        # Convert row to WorkingMemoryItem
        wm_item = self._row_to_item(row)

        # Route using ML or heuristic
        if use_ml and self.is_trained:
            features = self._extract_features(wm_item)
            prediction = self.model.predict([features])[0]
            confidence = max(self.model.predict_proba([features])[0])
            target_layer = TargetLayer(prediction)
        else:
            target_layer = self._heuristic_route(wm_item)
            confidence = 0.7

        # Log route
        with self.db.conn:
            self.db.conn.execute("""
                INSERT INTO consolidation_routes
                (wm_id, target_layer, confidence, routed_at)
                VALUES (?, ?, ?, datetime('now'))
            """, (item_id, target_layer.value, confidence))

        return {
            'item_id': item_id,
            'target_layer': target_layer.value,
            'confidence': confidence
        }

    def route_batch(self, project_id: int, item_ids: List[int]) -> List[dict]:
        """Route multiple items in batch."""
        return [self.route_item(project_id, item_id) for item_id in item_ids]

    def route(
        self,
        wm_item: WorkingMemoryItem,
        project_id: int
    ) -> Tuple[TargetLayer, float]:
        """
        Determine target layer for consolidation.

        Args:
            wm_item: Working memory item to route
            project_id: Project identifier

        Returns:
            Tuple of (target_layer, confidence)
        """
        # Extract features
        features = self._extract_features(wm_item)

        # Use ML model if trained, otherwise fall back to heuristics
        if self.is_trained and self.model is not None:
            prediction, confidence = self._ml_predict(features)
        else:
            prediction = self._heuristic_route(wm_item)
            confidence = 0.6  # Moderate confidence for heuristics

        # Log decision
        self._log_route_decision(
            wm_item.id,
            prediction,
            confidence,
            features
        )

        return prediction, confidence

    def consolidate_item(
        self,
        wm_item: WorkingMemoryItem,
        project_id: int,
        target_layer: Optional[TargetLayer] = None
    ) -> Dict:
        """
        Consolidate working memory item to long-term memory.

        Args:
            wm_item: Working memory item
            project_id: Project identifier
            target_layer: Optional override for target layer

        Returns:
            Dict with consolidation result
        """
        # Determine target if not specified
        if target_layer is None:
            target_layer, confidence = self.route(wm_item, project_id)
        else:
            confidence = 1.0  # User-specified, full confidence

        # Perform consolidation based on target layer
        ltm_id = self._consolidate_to_layer(wm_item, target_layer, project_id)

        # Remove from working memory
        with self.db.conn:
            self.db.conn.execute("""
                DELETE FROM working_memory WHERE id = ?
            """, (wm_item.id,))

        return {
            'wm_item_id': wm_item.id,
            'target_layer': target_layer.value,
            'ltm_id': ltm_id,
            'confidence': confidence
        }

    # ========================================================================
    # Feature Extraction
    # ========================================================================

    def _extract_features(self, wm_item: WorkingMemoryItem | int) -> np.ndarray:
        """
        Extract features for ML classification.

        Args:
            wm_item: WorkingMemoryItem object or item ID

        Features:
        1. Content length
        2. Is verbal (phonological loop)
        3. Is spatial (visuospatial sketchpad)
        4. Activation level
        5. Importance score
        6. Time in working memory (seconds)
        7. Has temporal markers (when, at, yesterday, etc.)
        8. Has action verbs (implement, fix, create, etc.)
        9. Has future markers (will, todo, reminder, etc.)
        10. Has question words (how, what, why, etc.)
        11. Has file references (path patterns)
        """
        # Accept either WorkingMemoryItem or int (item_id)
        if isinstance(wm_item, int):
            with self.db.conn:
                row = self.db.conn.execute("""
                    SELECT * FROM working_memory WHERE id = ?
                """, (wm_item,)).fetchone()
                if not row:
                    raise ValueError(f"Item {wm_item} not found")
                wm_item = self._row_to_item(row)

        content = wm_item.content.lower()

        features = [
            len(wm_item.content),  # 1. Content length
            1 if wm_item.component.value == 'phonological' else 0,  # 2. Is verbal
            1 if wm_item.component.value == 'visuospatial' else 0,  # 3. Is spatial
            wm_item.activation_level,  # 4. Activation
            wm_item.importance_score,  # 5. Importance
            (datetime.now() - wm_item.created_at).total_seconds(),  # 6. Time in WM
            self._has_temporal_markers(content),  # 7. Temporal
            self._has_action_verbs(content),  # 8. Action
            self._has_future_markers(content),  # 9. Future
            self._has_question_words(content),  # 10. Questions
            self._has_file_references(wm_item.content)  # 11. Files
        ]

        return np.array(features, dtype=float)

    def _has_temporal_markers(self, content: str) -> int:
        """Check for temporal markers (episodic memory indicators)."""
        markers = [
            r'\bwhen\b', r'\bat\b', r'\bon\b', r'\byesterday\b', r'\btoday\b', r'\btomorrow\b',
            r'\blast week\b', r'\boccurred\b', r'\bhappened\b', r'\bduring\b', r'\bwhile\b',
            r'\bbefore\b', r'\bafter\b', r'\bsince\b', r'\buntil\b', r'\d{1,2}:\d{2}',  # time patterns
            r'\d{4}-\d{2}-\d{2}'  # date patterns
        ]
        return int(any(re.search(marker, content) for marker in markers))

    def _has_action_verbs(self, content: str) -> int:
        """Check for action verbs (procedural memory indicators)."""
        verbs = [
            'implement', 'fix', 'create', 'update', 'delete', 'test',
            'deploy', 'configure', 'setup', 'build', 'run', 'execute',
            'install', 'compile', 'debug', 'refactor', 'optimize',
            'how to', 'step', 'procedure', 'workflow', 'process'
        ]
        return int(any(verb in content for verb in verbs))

    def _has_future_markers(self, content: str) -> int:
        """Check for future markers (prospective memory indicators)."""
        markers = [
            'will', 'todo', 'task', 'reminder', 'scheduled', 'plan',
            'need to', 'should', 'must', 'going to', 'next', 'later',
            'upcoming', 'deadline', 'due'
        ]
        return int(any(marker in content for marker in markers))

    def _has_question_words(self, content: str) -> int:
        """Check for question words (procedural/semantic indicators)."""
        questions = ['how', 'what', 'why', 'when', 'where', 'which', 'who']
        return int(any(content.startswith(q) for q in questions) or '?' in content)

    def _has_file_references(self, content: str) -> int:
        """Check for file path references (spatial/procedural indicators)."""
        patterns = [
            r'\.py$', r'\.js$', r'\.ts$', r'\.java$', r'\.cpp$',
            r'/', r'\\', r'\.\w+$'
        ]
        return int(any(re.search(pattern, content) for pattern in patterns))

    def _has_temporal_indicators(self, text: str) -> bool:
        """Check if text has temporal markers."""
        return bool(self._has_temporal_markers(text))

    def _has_procedural_patterns(self, text: str) -> bool:
        """Check if text has procedural workflow patterns."""
        procedural_keywords = [r'\bthen\b', r'\bnext\b', r'\bfirst\b', r'\bfinally\b',
                               r'\bstep\b', r'\brun\b', r'\bexecute\b',
                               r'\bdeploy\b', r'\bbuild\b', r'\binstall\b', r'\bconfigure\b']
        return any(re.search(keyword, text.lower()) for keyword in procedural_keywords)

    # ========================================================================
    # ML Model
    # ========================================================================

    def train(self, project_id: int, min_samples: int = 10) -> bool:
        """
        Train model on historical consolidation decisions.

        Args:
            project_id: Project identifier
            min_samples: Minimum training samples required

        Returns:
            True if training succeeded
        """
        # Fetch training data
        with self.db.conn:
            rows = self.db.conn.execute("""
                SELECT wm.*, cr.target_layer, cr.features
                FROM consolidation_routes cr
                JOIN working_memory wm ON cr.wm_id = wm.id
                WHERE wm.project_id = ? AND cr.was_correct = 1
            """, (project_id,)).fetchall()

        if len(rows) < min_samples:
            print(f"Insufficient training data: {len(rows)} samples (need >= {min_samples})")
            return False

        # Extract features and labels
        X = []
        y = []

        for row in rows:
            # Use stored features if available
            if row['features']:
                features = json.loads(row['features'])
                X.append(features)
            else:
                # Reconstruct working memory item and extract features
                wm_item = self._row_to_item(row)
                features = self._extract_features(wm_item)
                X.append(features.tolist())

            y.append(row['target_layer'])

        X = np.array(X)
        y = np.array(y)

        # Train Random Forest
        try:
            from sklearn.ensemble import RandomForestClassifier
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                random_state=42
            )
            self.model.fit(X, y)
            self.is_trained = True

            print(f"Model trained on {len(rows)} samples")
            print(f"Classes: {self.model.classes_}")
            print(f"Feature importance: {dict(zip(self.feature_names, self.model.feature_importances_))}")

            return True

        except ImportError:
            print("sklearn not installed, using heuristics only")
            return False

    def _ml_predict(self, features: np.ndarray) -> Tuple[TargetLayer, float]:
        """Make prediction using ML model."""
        prediction = self.model.predict([features])[0]
        probabilities = self.model.predict_proba([features])[0]
        confidence = float(np.max(probabilities))

        return TargetLayer(prediction), confidence

    # ========================================================================
    # Heuristic Fallback
    # ========================================================================

    def _heuristic_route(self, wm_item: WorkingMemoryItem | str) -> TargetLayer:
        """
        Fallback heuristic routing when ML model not available.

        Rules:
        - Temporal markers → episodic
        - Action/procedure markers → procedural
        - Future markers → prospective
        - Default → semantic
        """
        # Accept either WorkingMemoryItem or string
        content = wm_item.content.lower() if isinstance(wm_item, WorkingMemoryItem) else wm_item.lower()

        # Check temporal markers (episodic)
        if self._has_temporal_markers(content):
            return TargetLayer.EPISODIC

        # Check action verbs (procedural)
        if self._has_action_verbs(content):
            return TargetLayer.PROCEDURAL

        # Check future markers (prospective)
        if self._has_future_markers(content):
            return TargetLayer.PROSPECTIVE

        # Default to semantic
        return TargetLayer.SEMANTIC

    # ========================================================================
    # Consolidation Execution
    # ========================================================================

    def _consolidate_to_layer(
        self,
        wm_item: WorkingMemoryItem,
        target_layer: TargetLayer,
        project_id: int
    ) -> int:
        """
        Execute consolidation to target layer.

        Returns:
            ID in target layer
        """
        with self.db.conn:
            if target_layer == TargetLayer.SEMANTIC:
                # Insert into semantic_memory
                cursor = self.db.conn.execute("""
                    INSERT INTO semantic_memory
                    (project_id, content, memory_type, metadata)
                    VALUES (?, ?, 'fact', ?)
                """, (
                    project_id,
                    wm_item.content,
                    json.dumps({
                        'source': 'working_memory',
                        'wm_id': wm_item.id,
                        'importance': wm_item.importance_score
                    })
                ))
                return cursor.lastrowid

            elif target_layer == TargetLayer.EPISODIC:
                # Insert into episodic_events
                cursor = self.db.conn.execute("""
                    INSERT INTO episodic_events
                    (project_id, event_type, content, metadata)
                    VALUES (?, 'action', ?, ?)
                """, (
                    project_id,
                    wm_item.content,
                    json.dumps({
                        'source': 'working_memory',
                        'wm_id': wm_item.id
                    })
                ))
                return cursor.lastrowid

            elif target_layer == TargetLayer.PROCEDURAL:
                # Insert into procedural_templates
                cursor = self.db.conn.execute("""
                    INSERT INTO procedural_templates
                    (project_id, name, category, template, metadata)
                    VALUES (?, ?, 'workflow', ?, ?)
                """, (
                    project_id,
                    f"Procedure from WM #{wm_item.id}",
                    wm_item.content,
                    json.dumps({
                        'source': 'working_memory',
                        'wm_id': wm_item.id
                    })
                ))
                return cursor.lastrowid

            elif target_layer == TargetLayer.PROSPECTIVE:
                # Insert into prospective_tasks
                cursor = self.db.conn.execute("""
                    INSERT INTO prospective_tasks
                    (project_id, content, active_form, priority, metadata)
                    VALUES (?, ?, ?, 'medium', ?)
                """, (
                    project_id,
                    wm_item.content,
                    f"Working on: {wm_item.content[:50]}",
                    json.dumps({
                        'source': 'working_memory',
                        'wm_id': wm_item.id
                    })
                ))
                return cursor.lastrowid

            else:
                raise ValueError(f"Unknown target layer: {target_layer}")

    # ========================================================================
    # Feedback & Online Learning
    # ========================================================================

    def provide_feedback(
        self,
        route_id: int,
        was_correct: bool,
        correct_layer: Optional[TargetLayer] = None
    ):
        """
        Provide feedback on routing decision for online learning.

        Args:
            route_id: Consolidation route ID
            was_correct: Whether the route was correct
            correct_layer: Correct layer if route was wrong
        """
        with self.db.conn:
            self.db.conn.execute("""
                UPDATE consolidation_routes
                SET was_correct = ?
                WHERE id = ?
            """, (was_correct, route_id))

            if not was_correct and correct_layer:
                # Create corrected training example
                route = self.db.conn.execute("""
                    SELECT * FROM consolidation_routes WHERE id = ?
                """, (route_id,)).fetchone()

                if route:
                    self.db.conn.execute("""
                        INSERT INTO consolidation_routes
                        (wm_id, target_layer, confidence, was_correct, features)
                        VALUES (?, ?, 1.0, 1, ?)
                    """, (
                        route['wm_id'],
                        correct_layer.value,
                        route['features']
                    ))

        # Trigger retraining if enough feedback accumulated
        # (Implementation: could trigger async retraining)

    def get_routing_statistics(self, project_id: int) -> Dict:
        """Get statistics on routing decisions."""
        with self.db.conn:
            # Overall stats
            total = self.db.conn.execute("""
                SELECT COUNT(*) as count FROM consolidation_routes cr
                JOIN working_memory wm ON cr.wm_id = wm.id
                WHERE wm.project_id = ?
            """, (project_id,)).fetchone()

            # By layer
            by_layer = self.db.conn.execute("""
                SELECT target_layer, COUNT(*) as count,
                       AVG(confidence) as avg_confidence
                FROM consolidation_routes cr
                JOIN working_memory wm ON cr.wm_id = wm.id
                WHERE wm.project_id = ?
                GROUP BY target_layer
            """, (project_id,)).fetchall()

            # Accuracy (where feedback provided)
            accuracy = self.db.conn.execute("""
                SELECT
                    COUNT(*) as total_feedback,
                    SUM(CASE WHEN was_correct = 1 THEN 1 ELSE 0 END) as correct
                FROM consolidation_routes cr
                JOIN working_memory wm ON cr.wm_id = wm.id
                WHERE wm.project_id = ? AND was_correct IS NOT NULL
            """, (project_id,)).fetchone()

            return {
                'total_routes': total['count'],
                'by_layer': {row['target_layer']: {
                    'count': row['count'],
                    'avg_confidence': row['avg_confidence']
                } for row in by_layer},
                'accuracy': (
                    accuracy['correct'] / accuracy['total_feedback']
                    if accuracy['total_feedback'] > 0 else None
                ),
                'feedback_count': accuracy['total_feedback'],
                'is_trained': self.is_trained
            }

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _log_route_decision(
        self,
        wm_id: int,
        target_layer: TargetLayer,
        confidence: float,
        features: np.ndarray
    ):
        """Log routing decision for training/analysis."""
        with self.db.conn:
            self.db.conn.execute("""
                INSERT INTO consolidation_routes
                (wm_id, target_layer, confidence, features)
                VALUES (?, ?, ?, ?)
            """, (
                wm_id,
                target_layer.value,
                confidence,
                json.dumps(features.tolist())
            ))

    def _row_to_item(self, row) -> WorkingMemoryItem:
        """Convert database row to WorkingMemoryItem."""
        return WorkingMemoryItem.from_db_row(row)
