"""
Unit tests for the ModelRegistry module.

Tests cover:
- Model registration and versioning
- Model retrieval and listing
- A/B testing configuration
- Traffic routing
- Performance tracking
- Model rollback
"""

import pytest
import tempfile
import shutil
import os
from datetime import datetime
import sys
sys.path.insert(0, '/home/user1-gpu/Desktop/grants_folder/datagod/DataGod1')

from datagod.ml.model_registry import (
    ModelRegistry,
    ModelMetadata,
    ModelType,
    ModelStatus,
    ModelMetrics,
    ABTestConfig,
)


class TestModelRegistry:
    """Tests for ModelRegistry class."""
    
    @pytest.fixture
    def temp_registry_path(self):
        """Create a temporary directory for registry."""
        path = tempfile.mkdtemp()
        yield path
        shutil.rmtree(path, ignore_errors=True)
    
    @pytest.fixture
    def registry(self, temp_registry_path):
        """Create a registry instance."""
        return ModelRegistry(temp_registry_path)
    
    @pytest.fixture
    def sample_metrics(self):
        """Sample model metrics."""
        return ModelMetrics(
            accuracy=0.95,
            precision=0.92,
            recall=0.88,
            f1_score=0.90,
            latency_ms=15.5,
            memory_mb=256.0,
        )
    
    def test_registry_initialization(self, registry, temp_registry_path):
        """Test registry initializes correctly."""
        assert registry is not None
        assert registry.registry_path == temp_registry_path
    
    def test_register_model(self, registry, sample_metrics):
        """Test registering a new model."""
        model_id = registry.register_model(
            name="test_predictor",
            model_type=ModelType.SKLEARN,
            version="1.0.0",
            model_data={"type": "RandomForest", "n_estimators": 100},
            metrics=sample_metrics,
            description="Test model for predictions",
        )
        
        assert model_id is not None
        assert isinstance(model_id, str)
    
    def test_get_model(self, registry, sample_metrics):
        """Test retrieving a registered model."""
        model_id = registry.register_model(
            name="test_model",
            model_type=ModelType.PYTORCH,
            version="1.0.0",
            model_data={"layers": [128, 64, 32]},
            metrics=sample_metrics,
        )
        
        model = registry.get_model(model_id)
        
        assert model is not None
        assert model.name == "test_model"
        assert model.version == "1.0.0"
        assert model.model_type == ModelType.PYTORCH
    
    def test_list_models(self, registry, sample_metrics):
        """Test listing all models."""
        # Register multiple models
        registry.register_model(
            name="model_a",
            model_type=ModelType.SKLEARN,
            version="1.0.0",
            model_data={},
            metrics=sample_metrics,
        )
        registry.register_model(
            name="model_b",
            model_type=ModelType.TENSORFLOW,
            version="1.0.0",
            model_data={},
            metrics=sample_metrics,
        )
        
        models = registry.list_models()
        
        assert len(models) >= 2
        names = [m.name for m in models]
        assert "model_a" in names
        assert "model_b" in names
    
    def test_get_model_versions(self, registry, sample_metrics):
        """Test getting all versions of a model."""
        # Register multiple versions
        registry.register_model(
            name="versioned_model",
            model_type=ModelType.SKLEARN,
            version="1.0.0",
            model_data={},
            metrics=sample_metrics,
        )
        registry.register_model(
            name="versioned_model",
            model_type=ModelType.SKLEARN,
            version="1.1.0",
            model_data={},
            metrics=sample_metrics,
        )
        registry.register_model(
            name="versioned_model",
            model_type=ModelType.SKLEARN,
            version="2.0.0",
            model_data={},
            metrics=sample_metrics,
        )
        
        versions = registry.get_model_versions("versioned_model")
        
        assert len(versions) == 3
        version_nums = [v.version for v in versions]
        assert "1.0.0" in version_nums
        assert "1.1.0" in version_nums
        assert "2.0.0" in version_nums
    
    def test_activate_model(self, registry, sample_metrics):
        """Test activating a model version."""
        model_id = registry.register_model(
            name="activation_test",
            model_type=ModelType.SKLEARN,
            version="1.0.0",
            model_data={},
            metrics=sample_metrics,
        )
        
        result = registry.activate_model(model_id)
        
        assert result is True
        
        model = registry.get_model(model_id)
        assert model.status == ModelStatus.ACTIVE
    
    def test_get_active_model(self, registry, sample_metrics):
        """Test getting the active model for a name."""
        registry.register_model(
            name="active_test",
            model_type=ModelType.SKLEARN,
            version="1.0.0",
            model_data={},
            metrics=sample_metrics,
        )
        model_id = registry.register_model(
            name="active_test",
            model_type=ModelType.SKLEARN,
            version="2.0.0",
            model_data={},
            metrics=sample_metrics,
        )
        
        registry.activate_model(model_id)
        
        active = registry.get_active_model("active_test")
        
        assert active is not None
        assert active.version == "2.0.0"
    
    def test_rollback_model(self, registry, sample_metrics):
        """Test rolling back to a previous version."""
        v1_id = registry.register_model(
            name="rollback_test",
            model_type=ModelType.SKLEARN,
            version="1.0.0",
            model_data={},
            metrics=sample_metrics,
        )
        v2_id = registry.register_model(
            name="rollback_test",
            model_type=ModelType.SKLEARN,
            version="2.0.0",
            model_data={},
            metrics=sample_metrics,
        )
        
        registry.activate_model(v2_id)
        
        # Rollback to v1
        result = registry.rollback_model("rollback_test", v1_id)
        
        assert result is True
        
        active = registry.get_active_model("rollback_test")
        assert active.version == "1.0.0"
    
    def test_model_not_found(self, registry):
        """Test handling of non-existent model."""
        model = registry.get_model("non_existent_id")
        assert model is None
    
    def test_update_metrics(self, registry, sample_metrics):
        """Test updating model metrics."""
        model_id = registry.register_model(
            name="metrics_test",
            model_type=ModelType.SKLEARN,
            version="1.0.0",
            model_data={},
            metrics=sample_metrics,
        )
        
        new_metrics = ModelMetrics(
            accuracy=0.98,
            precision=0.96,
            recall=0.94,
            f1_score=0.95,
            latency_ms=12.0,
            memory_mb=200.0,
        )
        
        result = registry.update_metrics(model_id, new_metrics)
        
        assert result is True
        
        model = registry.get_model(model_id)
        assert model.metrics.accuracy == 0.98


class TestABTestConfig:
    """Tests for A/B testing configuration."""
    
    @pytest.fixture
    def temp_registry_path(self):
        """Create a temporary directory for registry."""
        path = tempfile.mkdtemp()
        yield path
        shutil.rmtree(path, ignore_errors=True)
    
    @pytest.fixture
    def registry(self, temp_registry_path):
        """Create a registry instance."""
        return ModelRegistry(temp_registry_path)
    
    @pytest.fixture
    def sample_metrics(self):
        """Sample model metrics."""
        return ModelMetrics(
            accuracy=0.95,
            precision=0.92,
            recall=0.88,
            f1_score=0.90,
            latency_ms=15.5,
            memory_mb=256.0,
        )
    
    def test_create_ab_test(self, registry, sample_metrics):
        """Test creating an A/B test."""
        v1_id = registry.register_model(
            name="ab_test_model",
            model_type=ModelType.SKLEARN,
            version="1.0.0",
            model_data={},
            metrics=sample_metrics,
        )
        v2_id = registry.register_model(
            name="ab_test_model",
            model_type=ModelType.SKLEARN,
            version="2.0.0",
            model_data={},
            metrics=sample_metrics,
        )
        
        config = ABTestConfig(
            name="test_ab",
            control_model_id=v1_id,
            treatment_model_id=v2_id,
            traffic_split=0.5,
        )
        
        result = registry.create_ab_test(config)
        
        assert result is True
    
    def test_get_model_for_request(self, registry, sample_metrics):
        """Test traffic routing for A/B test."""
        v1_id = registry.register_model(
            name="routing_model",
            model_type=ModelType.SKLEARN,
            version="1.0.0",
            model_data={},
            metrics=sample_metrics,
        )
        v2_id = registry.register_model(
            name="routing_model",
            model_type=ModelType.SKLEARN,
            version="2.0.0",
            model_data={},
            metrics=sample_metrics,
        )
        
        config = ABTestConfig(
            name="routing_test",
            control_model_id=v1_id,
            treatment_model_id=v2_id,
            traffic_split=0.5,
        )
        
        registry.create_ab_test(config)
        
        # Get model for multiple requests
        results = [registry.get_model_for_request("routing_model", f"user_{i}") 
                   for i in range(100)]
        
        # Should have both versions represented
        versions = [r.version for r in results if r]
        assert "1.0.0" in versions
        assert "2.0.0" in versions


class TestModelMetrics:
    """Tests for ModelMetrics dataclass."""
    
    def test_metrics_creation(self):
        """Test creating metrics."""
        metrics = ModelMetrics(
            accuracy=0.95,
            precision=0.92,
            recall=0.88,
            f1_score=0.90,
        )
        
        assert metrics.accuracy == 0.95
        assert metrics.precision == 0.92
    
    def test_metrics_optional_fields(self):
        """Test metrics with optional fields."""
        metrics = ModelMetrics(
            accuracy=0.95,
        )
        
        assert metrics.accuracy == 0.95
        assert metrics.precision is None


class TestModelStatus:
    """Tests for ModelStatus enum."""
    
    def test_all_statuses_defined(self):
        """Test that all statuses are defined."""
        assert ModelStatus.REGISTERED is not None
        assert ModelStatus.ACTIVE is not None
        assert ModelStatus.DEPRECATED is not None
        assert ModelStatus.ARCHIVED is not None
