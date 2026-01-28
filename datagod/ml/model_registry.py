"""
DataGod Model Registry

Model versioning, A/B testing, rollback capability, and performance tracking
for machine learning models.
"""

import logging
import os
import json
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import shutil

logger = logging.getLogger(__name__)


class ModelStatus(str, Enum):
    """Model deployment status."""
    TRAINING = "training"
    STAGED = "staged"
    PRODUCTION = "production"
    ARCHIVED = "archived"
    FAILED = "failed"


class ModelType(str, Enum):
    """Types of models supported."""
    NEURAL_NETWORK = "neural_network"
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    LSTM = "lstm"
    TRANSFORMER = "transformer"
    SKLEARN = "sklearn"
    CUSTOM = "custom"


@dataclass
class ModelMetrics:
    """Performance metrics for a model."""
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    mse: Optional[float] = None
    mae: Optional[float] = None
    r2_score: Optional[float] = None
    auc_roc: Optional[float] = None
    inference_time_ms: Optional[float] = None
    training_time_seconds: Optional[float] = None
    custom_metrics: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelMetrics':
        custom = data.pop('custom_metrics', {})
        metrics = cls(**{k: v for k, v in data.items() if k in cls.__annotations__})
        metrics.custom_metrics = custom
        return metrics


@dataclass
class ModelVersion:
    """Represents a specific version of a model."""
    version_id: str
    model_name: str
    version_number: str  # Semantic versioning: 1.0.0
    model_type: ModelType
    status: ModelStatus
    created_at: datetime
    created_by: str
    description: str
    file_path: str
    file_size_bytes: int
    config: Dict[str, Any]
    metrics: ModelMetrics
    parent_version: Optional[str] = None
    ab_test_group: Optional[str] = None  # 'control' or 'treatment'
    traffic_percentage: float = 0.0
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id": self.version_id,
            "model_name": self.model_name,
            "version_number": self.version_number,
            "model_type": self.model_type.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "description": self.description,
            "file_path": self.file_path,
            "file_size_bytes": self.file_size_bytes,
            "config": self.config,
            "metrics": self.metrics.to_dict(),
            "parent_version": self.parent_version,
            "ab_test_group": self.ab_test_group,
            "traffic_percentage": self.traffic_percentage,
            "tags": self.tags,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelVersion':
        data['model_type'] = ModelType(data['model_type'])
        data['status'] = ModelStatus(data['status'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['metrics'] = ModelMetrics.from_dict(data['metrics'])
        return cls(**data)


@dataclass
class ABTest:
    """A/B test configuration."""
    test_id: str
    test_name: str
    model_name: str
    control_version_id: str
    treatment_version_id: str
    control_traffic_pct: float
    treatment_traffic_pct: float
    start_date: datetime
    end_date: Optional[datetime]
    status: str  # 'running', 'completed', 'cancelled'
    metrics_to_compare: List[str]
    winner: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "model_name": self.model_name,
            "control_version_id": self.control_version_id,
            "treatment_version_id": self.treatment_version_id,
            "control_traffic_pct": self.control_traffic_pct,
            "treatment_traffic_pct": self.treatment_traffic_pct,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "status": self.status,
            "metrics_to_compare": self.metrics_to_compare,
            "winner": self.winner,
            "created_at": self.created_at.isoformat(),
        }


class ModelRegistry:
    """
    Centralized model registry for versioning, A/B testing, and deployment.
    
    Features:
    - Model versioning with semantic versioning
    - A/B testing with traffic splitting
    - Rollback capability
    - Performance tracking across versions
    - Model comparison
    """
    
    def __init__(self, registry_path: str = None):
        """Initialize the model registry."""
        self.registry_path = Path(registry_path or os.environ.get(
            'MODEL_REGISTRY_PATH', 
            os.path.join(os.path.expanduser('~'), '.datagod', 'models')
        ))
        self.registry_path.mkdir(parents=True, exist_ok=True)
        
        self.models_path = self.registry_path / 'models'
        self.metadata_path = self.registry_path / 'metadata'
        self.models_path.mkdir(exist_ok=True)
        self.metadata_path.mkdir(exist_ok=True)
        
        self._versions: Dict[str, ModelVersion] = {}
        self._ab_tests: Dict[str, ABTest] = {}
        self._load_metadata()
        
        logger.info("ModelRegistry initialized at %s", self.registry_path)
    
    def register_model(
        self,
        model_name: str,
        version_number: str,
        model_type: ModelType,
        model_path: str,
        config: Dict[str, Any],
        metrics: ModelMetrics,
        description: str = "",
        created_by: str = "system",
        tags: List[str] = None,
        parent_version: str = None
    ) -> ModelVersion:
        """
        Register a new model version.
        
        Args:
            model_name: Name of the model
            version_number: Semantic version (e.g., '1.0.0')
            model_type: Type of model
            model_path: Path to trained model file
            config: Training configuration
            metrics: Performance metrics
            description: Version description
            created_by: Creator username
            tags: Optional tags
            parent_version: ID of parent version if evolved
            
        Returns:
            ModelVersion object
        """
        # Generate version ID
        version_id = self._generate_version_id(model_name, version_number)
        
        # Check if version already exists
        if version_id in self._versions:
            raise ValueError(f"Version {version_number} already exists for model {model_name}")
        
        # Copy model to registry
        model_file = Path(model_path)
        if not model_file.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        dest_dir = self.models_path / model_name / version_number
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / model_file.name
        shutil.copy2(model_path, dest_path)
        
        # Create version record
        version = ModelVersion(
            version_id=version_id,
            model_name=model_name,
            version_number=version_number,
            model_type=model_type,
            status=ModelStatus.STAGED,
            created_at=datetime.utcnow(),
            created_by=created_by,
            description=description,
            file_path=str(dest_path),
            file_size_bytes=dest_path.stat().st_size,
            config=config,
            metrics=metrics,
            parent_version=parent_version,
            tags=tags or [],
        )
        
        self._versions[version_id] = version
        self._save_metadata()
        
        logger.info("Registered model %s version %s", model_name, version_number)
        return version
    
    def promote_to_production(self, version_id: str, traffic_percentage: float = 100.0) -> ModelVersion:
        """
        Promote a model version to production.
        
        Args:
            version_id: Version ID to promote
            traffic_percentage: Percentage of traffic to route (for gradual rollout)
            
        Returns:
            Updated ModelVersion
        """
        if version_id not in self._versions:
            raise ValueError(f"Version not found: {version_id}")
        
        version = self._versions[version_id]
        
        # Demote current production versions
        for v in self._versions.values():
            if v.model_name == version.model_name and v.status == ModelStatus.PRODUCTION:
                if traffic_percentage == 100:
                    v.status = ModelStatus.ARCHIVED
                    v.traffic_percentage = 0.0
                else:
                    v.traffic_percentage = 100 - traffic_percentage
        
        # Promote new version
        version.status = ModelStatus.PRODUCTION
        version.traffic_percentage = traffic_percentage
        
        self._save_metadata()
        logger.info("Promoted %s to production with %s%% traffic", version_id, traffic_percentage)
        
        return version
    
    def rollback(self, model_name: str, target_version: str = None) -> ModelVersion:
        """
        Rollback to a previous version.
        
        Args:
            model_name: Model to rollback
            target_version: Specific version to rollback to (default: previous production)
            
        Returns:
            Restored ModelVersion
        """
        # Find versions for this model
        model_versions = [v for v in self._versions.values() if v.model_name == model_name]
        model_versions.sort(key=lambda x: x.created_at, reverse=True)
        
        if len(model_versions) < 2:
            raise ValueError(f"No previous version available for rollback: {model_name}")
        
        # Find target version
        if target_version:
            target = next((v for v in model_versions if v.version_number == target_version), None)
            if not target:
                raise ValueError(f"Target version not found: {target_version}")
        else:
            # Find most recent archived version
            target = next(
                (v for v in model_versions if v.status == ModelStatus.ARCHIVED),
                model_versions[1]  # Fallback to second most recent
            )
        
        # Demote current production
        for v in model_versions:
            if v.status == ModelStatus.PRODUCTION:
                v.status = ModelStatus.ARCHIVED
                v.traffic_percentage = 0.0
        
        # Promote target
        target.status = ModelStatus.PRODUCTION
        target.traffic_percentage = 100.0
        
        self._save_metadata()
        logger.info("Rolled back %s to version %s", model_name, target.version_number)
        
        return target
    
    def start_ab_test(
        self,
        test_name: str,
        model_name: str,
        control_version_id: str,
        treatment_version_id: str,
        control_traffic_pct: float = 50.0,
        metrics_to_compare: List[str] = None
    ) -> ABTest:
        """
        Start an A/B test between two model versions.
        
        Args:
            test_name: Name for the test
            model_name: Model being tested
            control_version_id: Control version ID
            treatment_version_id: Treatment version ID
            control_traffic_pct: Traffic % for control (remainder goes to treatment)
            metrics_to_compare: Metrics to compare for winner selection
            
        Returns:
            ABTest configuration
        """
        if control_version_id not in self._versions:
            raise ValueError(f"Control version not found: {control_version_id}")
        if treatment_version_id not in self._versions:
            raise ValueError(f"Treatment version not found: {treatment_version_id}")
        
        test_id = hashlib.md5(f"{model_name}_{test_name}_{datetime.utcnow().isoformat()}".encode()).hexdigest()[:12]
        
        # Update traffic routing
        self._versions[control_version_id].ab_test_group = 'control'
        self._versions[control_version_id].traffic_percentage = control_traffic_pct
        self._versions[control_version_id].status = ModelStatus.PRODUCTION
        
        self._versions[treatment_version_id].ab_test_group = 'treatment'
        self._versions[treatment_version_id].traffic_percentage = 100 - control_traffic_pct
        self._versions[treatment_version_id].status = ModelStatus.PRODUCTION
        
        ab_test = ABTest(
            test_id=test_id,
            test_name=test_name,
            model_name=model_name,
            control_version_id=control_version_id,
            treatment_version_id=treatment_version_id,
            control_traffic_pct=control_traffic_pct,
            treatment_traffic_pct=100 - control_traffic_pct,
            start_date=datetime.utcnow(),
            end_date=None,
            status='running',
            metrics_to_compare=metrics_to_compare or ['accuracy', 'inference_time_ms'],
        )
        
        self._ab_tests[test_id] = ab_test
        self._save_metadata()
        
        logger.info("Started A/B test %s for model %s", test_name, model_name)
        return ab_test
    
    def complete_ab_test(self, test_id: str, winner: str = None) -> ABTest:
        """
        Complete an A/B test and optionally declare a winner.
        
        Args:
            test_id: Test ID
            winner: 'control' or 'treatment' or None for manual selection later
            
        Returns:
            Updated ABTest
        """
        if test_id not in self._ab_tests:
            raise ValueError(f"A/B test not found: {test_id}")
        
        ab_test = self._ab_tests[test_id]
        ab_test.end_date = datetime.utcnow()
        ab_test.status = 'completed'
        ab_test.winner = winner
        
        # Route all traffic to winner if declared
        if winner:
            winner_id = ab_test.control_version_id if winner == 'control' else ab_test.treatment_version_id
            loser_id = ab_test.treatment_version_id if winner == 'control' else ab_test.control_version_id
            
            self._versions[winner_id].traffic_percentage = 100.0
            self._versions[winner_id].ab_test_group = None
            
            self._versions[loser_id].status = ModelStatus.ARCHIVED
            self._versions[loser_id].traffic_percentage = 0.0
            self._versions[loser_id].ab_test_group = None
        
        self._save_metadata()
        logger.info("Completed A/B test %s, winner: %s", test_id, winner)
        
        return ab_test
    
    def get_production_model(self, model_name: str) -> Optional[str]:
        """
        Get the file path for the production model.
        
        Uses traffic routing for A/B tests.
        """
        import random
        
        production_versions = [
            v for v in self._versions.values()
            if v.model_name == model_name and v.status == ModelStatus.PRODUCTION
        ]
        
        if not production_versions:
            return None
        
        if len(production_versions) == 1:
            return production_versions[0].file_path
        
        # Traffic-based selection
        roll = random.random() * 100
        cumulative = 0
        for v in production_versions:
            cumulative += v.traffic_percentage
            if roll < cumulative:
                return v.file_path
        
        return production_versions[0].file_path
    
    def get_version(self, version_id: str) -> Optional[ModelVersion]:
        """Get a specific model version."""
        return self._versions.get(version_id)
    
    def list_versions(
        self,
        model_name: str = None,
        status: ModelStatus = None,
        limit: int = 100
    ) -> List[ModelVersion]:
        """List model versions with optional filters."""
        versions = list(self._versions.values())
        
        if model_name:
            versions = [v for v in versions if v.model_name == model_name]
        
        if status:
            versions = [v for v in versions if v.status == status]
        
        versions.sort(key=lambda x: x.created_at, reverse=True)
        return versions[:limit]
    
    def compare_versions(self, version_id_1: str, version_id_2: str) -> Dict[str, Any]:
        """Compare metrics between two versions."""
        v1 = self._versions.get(version_id_1)
        v2 = self._versions.get(version_id_2)
        
        if not v1 or not v2:
            raise ValueError("One or both versions not found")
        
        m1 = v1.metrics.to_dict()
        m2 = v2.metrics.to_dict()
        
        comparison = {
            "version_1": {"id": version_id_1, "version": v1.version_number},
            "version_2": {"id": version_id_2, "version": v2.version_number},
            "metrics_comparison": {},
        }
        
        all_metrics = set(m1.keys()) | set(m2.keys())
        for metric in all_metrics:
            val1 = m1.get(metric)
            val2 = m2.get(metric)
            
            improvement = None
            if val1 is not None and val2 is not None and isinstance(val1, (int, float)):
                improvement = ((val2 - val1) / val1 * 100) if val1 != 0 else 0
            
            comparison["metrics_comparison"][metric] = {
                "version_1": val1,
                "version_2": val2,
                "improvement_pct": round(improvement, 2) if improvement else None,
            }
        
        return comparison
    
    def get_performance_history(self, model_name: str, metric: str) -> List[Dict[str, Any]]:
        """Get performance history for a metric across versions."""
        versions = self.list_versions(model_name=model_name)
        
        history = []
        for v in versions:
            metrics = v.metrics.to_dict()
            if metric in metrics:
                history.append({
                    "version": v.version_number,
                    "version_id": v.version_id,
                    "created_at": v.created_at.isoformat(),
                    "value": metrics[metric],
                    "status": v.status.value,
                })
        
        history.sort(key=lambda x: x["created_at"])
        return history
    
    def delete_version(self, version_id: str, force: bool = False) -> bool:
        """Delete a model version (archives by default)."""
        if version_id not in self._versions:
            return False
        
        version = self._versions[version_id]
        
        if version.status == ModelStatus.PRODUCTION and not force:
            raise ValueError("Cannot delete production version without force=True")
        
        if force:
            # Actually delete files
            model_path = Path(version.file_path)
            if model_path.exists():
                model_path.unlink()
            del self._versions[version_id]
        else:
            version.status = ModelStatus.ARCHIVED
        
        self._save_metadata()
        return True
    
    def _generate_version_id(self, model_name: str, version_number: str) -> str:
        """Generate a unique version ID."""
        return hashlib.md5(f"{model_name}_{version_number}".encode()).hexdigest()[:16]
    
    def _save_metadata(self) -> None:
        """Save registry metadata to disk."""
        metadata = {
            "versions": {k: v.to_dict() for k, v in self._versions.items()},
            "ab_tests": {k: v.to_dict() for k, v in self._ab_tests.items()},
            "last_updated": datetime.utcnow().isoformat(),
        }
        
        metadata_file = self.metadata_path / 'registry.json'
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def _load_metadata(self) -> None:
        """Load registry metadata from disk."""
        metadata_file = self.metadata_path / 'registry.json'
        
        if not metadata_file.exists():
            return
        
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            self._versions = {
                k: ModelVersion.from_dict(v)
                for k, v in metadata.get('versions', {}).items()
            }
            
            for test_data in metadata.get('ab_tests', {}).values():
                test_data['start_date'] = datetime.fromisoformat(test_data['start_date'])
                test_data['end_date'] = datetime.fromisoformat(test_data['end_date']) if test_data['end_date'] else None
                test_data['created_at'] = datetime.fromisoformat(test_data['created_at'])
                self._ab_tests[test_data['test_id']] = ABTest(**test_data)
            
            logger.info("Loaded %d model versions from registry", len(self._versions))
            
        except Exception as e:
            logger.error("Failed to load registry metadata: %s", e)


# Create default registry instance
_default_registry: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    """Get or create the default model registry instance."""
    global _default_registry
    if _default_registry is None:
        _default_registry = ModelRegistry()
    return _default_registry
