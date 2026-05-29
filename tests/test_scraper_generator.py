"""
Tests for Scraper Generator System
Tests the template-based scraper generation functionality
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from datagod.scrapers.scraper_generator import (
    ConfigValidationError,
    ScraperGenerator,
    ScraperGeneratorError,
    create_generator,
)


class TestScraperGenerator:
    """Tests for the ScraperGenerator class"""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            templates_dir = temp_path / "templates"
            configs_dir = temp_path / "configs"
            output_dir = temp_path / "output"

            templates_dir.mkdir()
            configs_dir.mkdir()
            output_dir.mkdir()

            yield {
                "templates": templates_dir,
                "configs": configs_dir,
                "output": output_dir,
            }

    @pytest.fixture
    def sample_config(self):
        """Sample state configuration"""
        return {
            "state_code": "XX",
            "state_name": "Test State",
            "auth_type": "api_key",
            "requests_per_minute": 60,
            "requests_per_hour": 1000,
            "timeout": 30,
            "counties": [
                {
                    "name": "Test County",
                    "base_url": "https://test.example.com/api",
                    "property_endpoint": "/property/search",
                    "deed_endpoint": "/deed/search",
                    "lien_endpoint": "/lien/search",
                    "requires_auth": True,
                    "rate_limit": 60,
                }
            ],
            "data_sources": {"property": {"type": "api", "url": "/property/search"}},
        }

    @pytest.fixture
    def sample_template(self):
        """Sample scraper template"""
        return '''"""
${STATE_NAME} State API Integration
Generated: ${GENERATED_DATE}
"""

class ${CLASS_NAME}:
    STATE_CODE = '${STATE_CODE}'
    STATE_NAME = '${STATE_NAME}'

    ${COUNTY_APIS}

    def __init__(self):
        pass
'''

    def test_generator_initialization(self, temp_dirs):
        """Test ScraperGenerator initialization"""
        generator = ScraperGenerator(
            templates_dir=str(temp_dirs["templates"]),
            configs_dir=str(temp_dirs["configs"]),
            output_dir=str(temp_dirs["output"]),
        )

        assert generator.templates_dir.exists()
        assert generator.configs_dir.exists()
        assert generator.output_dir.exists()

    def test_generator_default_initialization(self):
        """Test ScraperGenerator with default paths"""
        generator = create_generator()
        assert generator is not None
        assert generator.templates_dir.exists()
        assert generator.configs_dir.exists()

    def test_load_config_valid(self, temp_dirs, sample_config):
        """Test loading a valid configuration"""
        config_file = temp_dirs["configs"] / "xx.json"
        with open(config_file, "w") as f:
            json.dump(sample_config, f)

        generator = ScraperGenerator(
            templates_dir=str(temp_dirs["templates"]),
            configs_dir=str(temp_dirs["configs"]),
            output_dir=str(temp_dirs["output"]),
        )

        loaded = generator.load_config("XX")
        assert loaded["state_code"] == "XX"
        assert loaded["state_name"] == "Test State"
        assert len(loaded["counties"]) == 1

    def test_load_config_missing(self, temp_dirs):
        """Test loading a non-existent configuration"""
        generator = ScraperGenerator(
            templates_dir=str(temp_dirs["templates"]),
            configs_dir=str(temp_dirs["configs"]),
            output_dir=str(temp_dirs["output"]),
        )

        with pytest.raises(ConfigValidationError) as exc_info:
            generator.load_config("ZZ")

        assert "not found" in str(exc_info.value).lower()

    def test_load_config_invalid_json(self, temp_dirs):
        """Test loading an invalid JSON configuration"""
        config_file = temp_dirs["configs"] / "bad.json"
        with open(config_file, "w") as f:
            f.write("{ invalid json }")

        generator = ScraperGenerator(
            templates_dir=str(temp_dirs["templates"]),
            configs_dir=str(temp_dirs["configs"]),
            output_dir=str(temp_dirs["output"]),
        )

        with pytest.raises(ConfigValidationError):
            generator.load_config("bad")

    def test_validate_config_missing_required_fields(self, temp_dirs):
        """Test validation catches missing required fields"""
        generator = ScraperGenerator(
            templates_dir=str(temp_dirs["templates"]),
            configs_dir=str(temp_dirs["configs"]),
            output_dir=str(temp_dirs["output"]),
        )

        # Missing state_code
        invalid_config = {"state_name": "Test", "counties": []}

        with pytest.raises(ConfigValidationError) as exc_info:
            generator._validate_config(invalid_config)

        assert "state_code" in str(exc_info.value)

    def test_validate_config_invalid_state_code(self, temp_dirs):
        """Test validation catches invalid state code format"""
        generator = ScraperGenerator(
            templates_dir=str(temp_dirs["templates"]),
            configs_dir=str(temp_dirs["configs"]),
            output_dir=str(temp_dirs["output"]),
        )

        invalid_config = {
            "state_code": "XYZ",  # 3 letters, should be 2
            "state_name": "Test",
            "counties": [{"name": "Test County"}],
        }

        with pytest.raises(ConfigValidationError) as exc_info:
            generator._validate_config(invalid_config)

        assert "2-letter" in str(exc_info.value)

    def test_validate_config_empty_counties(self, temp_dirs):
        """Test validation catches empty counties list"""
        generator = ScraperGenerator(
            templates_dir=str(temp_dirs["templates"]),
            configs_dir=str(temp_dirs["configs"]),
            output_dir=str(temp_dirs["output"]),
        )

        invalid_config = {"state_code": "XX", "state_name": "Test", "counties": []}

        with pytest.raises(ConfigValidationError) as exc_info:
            generator._validate_config(invalid_config)

        assert "empty" in str(exc_info.value).lower()

    def test_load_template(self, temp_dirs, sample_template):
        """Test loading a template file"""
        template_file = temp_dirs["templates"] / "state_api_template.py"
        with open(template_file, "w") as f:
            f.write(sample_template)

        generator = ScraperGenerator(
            templates_dir=str(temp_dirs["templates"]),
            configs_dir=str(temp_dirs["configs"]),
            output_dir=str(temp_dirs["output"]),
        )

        loaded = generator.load_template("state_api_template")
        assert "${STATE_NAME}" in loaded
        assert "${CLASS_NAME}" in loaded

    def test_load_template_missing(self, temp_dirs):
        """Test loading a non-existent template"""
        generator = ScraperGenerator(
            templates_dir=str(temp_dirs["templates"]),
            configs_dir=str(temp_dirs["configs"]),
            output_dir=str(temp_dirs["output"]),
        )

        with pytest.raises(ScraperGeneratorError) as exc_info:
            generator.load_template("nonexistent")

        assert "not found" in str(exc_info.value).lower()

    def test_generate_county_apis(self, temp_dirs, sample_config):
        """Test COUNTY_APIS dictionary generation"""
        generator = ScraperGenerator(
            templates_dir=str(temp_dirs["templates"]),
            configs_dir=str(temp_dirs["configs"]),
            output_dir=str(temp_dirs["output"]),
        )

        county_apis = generator._generate_county_apis(sample_config["counties"])

        assert "COUNTY_APIS = {" in county_apis
        assert "'test_county':" in county_apis
        assert "'Test County'" in county_apis
        assert "/property/search" in county_apis

    def test_generate_scraper(self, temp_dirs, sample_config, sample_template):
        """Test scraper generation from config"""
        generator = ScraperGenerator(
            templates_dir=str(temp_dirs["templates"]),
            configs_dir=str(temp_dirs["configs"]),
            output_dir=str(temp_dirs["output"]),
        )

        code = generator.generate_scraper(sample_config, sample_template)

        assert "Test State" in code
        assert "TestStateAPI" in code
        assert "STATE_CODE" in code
        assert "XX" in code

    def test_validate_generated_code_valid(self, temp_dirs):
        """Test validation of syntactically correct code"""
        generator = ScraperGenerator(
            templates_dir=str(temp_dirs["templates"]),
            configs_dir=str(temp_dirs["configs"]),
            output_dir=str(temp_dirs["output"]),
        )

        valid_code = """
class TestAPI:
    def __init__(self):
        pass
"""
        assert generator.validate_generated_code(valid_code) is True

    def test_validate_generated_code_invalid(self, temp_dirs):
        """Test validation catches syntax errors"""
        generator = ScraperGenerator(
            templates_dir=str(temp_dirs["templates"]),
            configs_dir=str(temp_dirs["configs"]),
            output_dir=str(temp_dirs["output"]),
        )

        invalid_code = """
class TestAPI
    def __init__(self):  # Missing colon after class
        pass
"""
        with pytest.raises(ScraperGeneratorError) as exc_info:
            generator.validate_generated_code(invalid_code)

        assert "syntax" in str(exc_info.value).lower()

    def test_save_scraper(self, temp_dirs):
        """Test saving generated scraper to file"""
        generator = ScraperGenerator(
            templates_dir=str(temp_dirs["templates"]),
            configs_dir=str(temp_dirs["configs"]),
            output_dir=str(temp_dirs["output"]),
        )

        code = "class TestAPI:\n    pass\n"
        output_path = generator.save_scraper(code, "XX")

        assert output_path.exists()
        assert output_path.name == "xx_api.py"

        with open(output_path) as f:
            saved_code = f.read()
        assert saved_code == code

    def test_list_available_configs(self, temp_dirs, sample_config):
        """Test listing available configurations"""
        # Create some config files
        for code in ["aa", "bb", "cc"]:
            config = sample_config.copy()
            config["state_code"] = code.upper()
            with open(temp_dirs["configs"] / f"{code}.json", "w") as f:
                json.dump(config, f)

        generator = ScraperGenerator(
            templates_dir=str(temp_dirs["templates"]),
            configs_dir=str(temp_dirs["configs"]),
            output_dir=str(temp_dirs["output"]),
        )

        configs = generator.list_available_configs()
        assert "AA" in configs
        assert "BB" in configs
        assert "CC" in configs

    def test_get_coverage_report(self, temp_dirs):
        """Test coverage report generation"""
        generator = ScraperGenerator(
            templates_dir=str(temp_dirs["templates"]),
            configs_dir=str(temp_dirs["configs"]),
            output_dir=str(temp_dirs["output"]),
        )

        report = generator.get_coverage_report()

        assert "total_states" in report
        assert "coverage_percentage" in report
        assert "states_missing" in report
        assert report["total_states"] == 51  # 50 states + DC

    def test_get_auth_mixin(self, temp_dirs):
        """Test authentication mixin selection"""
        generator = ScraperGenerator(
            templates_dir=str(temp_dirs["templates"]),
            configs_dir=str(temp_dirs["configs"]),
            output_dir=str(temp_dirs["output"]),
        )

        assert generator._get_auth_mixin("api_key") == "APIKeyAuthentication"
        assert generator._get_auth_mixin("oauth2") == "OAuth2Authentication"
        assert generator._get_auth_mixin("hmac") == "HMACAuthentication"
        assert generator._get_auth_mixin("none") == ""


class TestScraperGeneratorIntegration:
    """Integration tests for scraper generation"""

    def test_generate_and_save_full_workflow(self):
        """Test the complete workflow of generating a scraper"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            templates_dir = temp_path / "templates"
            configs_dir = temp_path / "configs"
            output_dir = temp_path / "output"

            templates_dir.mkdir()
            configs_dir.mkdir()
            output_dir.mkdir()

            # Create template
            template = '''"""${STATE_NAME} API"""
class ${CLASS_NAME}:
    STATE_CODE = '${STATE_CODE}'
    ${COUNTY_APIS}
'''
            with open(templates_dir / "state_api_template.py", "w") as f:
                f.write(template)

            # Create config
            config = {
                "state_code": "XX",
                "state_name": "Test State",
                "auth_type": "none",
                "counties": [
                    {"name": "County A", "base_url": "https://a.test.com"},
                    {"name": "County B", "base_url": "https://b.test.com"},
                ],
            }
            with open(configs_dir / "xx.json", "w") as f:
                json.dump(config, f)

            # Generate
            generator = ScraperGenerator(
                templates_dir=str(templates_dir),
                configs_dir=str(configs_dir),
                output_dir=str(output_dir),
            )

            output_path = generator.generate_and_save("XX")

            # Verify
            assert output_path.exists()

            with open(output_path) as f:
                code = f.read()

            assert "Test State" in code
            assert "TestStateAPI" in code
            assert "county_a" in code
            assert "county_b" in code
