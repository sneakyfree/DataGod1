"""
Bulk Config Updater

Updates scraper configurations across multiple jurisdictions at once.
Useful for:
- Applying URL pattern changes across all state scrapers
- Updating API endpoints when services migrate
- Bulk enabling/disabling categories
- Syncing configuration with discovered endpoints
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable

logger = logging.getLogger(__name__)


class BulkConfigUpdater:
    """
    Bulk update scraper configurations.

    Features:
    - Update multiple config files at once
    - Pattern-based URL updates
    - Backup before changes
    - Dry-run mode
    - Change logging
    """

    def __init__(self, config_dir: str = None):
        """
        Initialize the bulk config updater.

        Args:
            config_dir: Directory containing config JSON files
        """
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = Path(__file__).parent.parent / 'configs'

        self.backup_dir = self.config_dir / 'backups'
        self.changes_log: List[Dict[str, Any]] = []

    def list_configs(self, pattern: str = "*.json") -> List[Path]:
        """List all config files matching pattern."""
        return list(self.config_dir.glob(pattern))

    def load_config(self, config_path: Path) -> Dict[str, Any]:
        """Load a config file."""
        with open(config_path, 'r') as f:
            return json.load(f)

    def save_config(self, config_path: Path, config: Dict[str, Any]):
        """Save a config file with proper formatting."""
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

    def backup_config(self, config_path: Path) -> Path:
        """Create a backup of a config file."""
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{config_path.stem}_{timestamp}.json"
        backup_path = self.backup_dir / backup_name

        with open(config_path, 'r') as src:
            with open(backup_path, 'w') as dst:
                dst.write(src.read())

        return backup_path

    def update_url_pattern(
        self,
        old_pattern: str,
        new_pattern: str,
        states: List[str] = None,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Update URL patterns across config files.

        Args:
            old_pattern: Pattern to find (substring match)
            new_pattern: Replacement pattern
            states: List of state codes to update (None = all)
            dry_run: If True, don't actually make changes

        Returns:
            Summary of changes made
        """
        results = {
            'files_checked': 0,
            'files_modified': 0,
            'changes': [],
            'dry_run': dry_run
        }

        for config_path in self.list_configs():
            state_code = config_path.stem.upper()

            # Filter by state if specified
            if states and state_code not in states:
                continue

            results['files_checked'] += 1

            try:
                config = self.load_config(config_path)
                modified = False
                file_changes = []

                # Update URLs in endpoints
                if 'endpoints' in config:
                    for endpoint_name, endpoint_config in config['endpoints'].items():
                        if 'url' in endpoint_config and old_pattern in endpoint_config['url']:
                            old_url = endpoint_config['url']
                            new_url = old_url.replace(old_pattern, new_pattern)

                            file_changes.append({
                                'endpoint': endpoint_name,
                                'field': 'url',
                                'old': old_url,
                                'new': new_url
                            })

                            if not dry_run:
                                endpoint_config['url'] = new_url
                                modified = True

                # Update base_url if present
                if 'base_url' in config and old_pattern in config['base_url']:
                    old_url = config['base_url']
                    new_url = old_url.replace(old_pattern, new_pattern)

                    file_changes.append({
                        'endpoint': 'base_url',
                        'field': 'base_url',
                        'old': old_url,
                        'new': new_url
                    })

                    if not dry_run:
                        config['base_url'] = new_url
                        modified = True

                if file_changes:
                    results['changes'].append({
                        'file': str(config_path),
                        'state': state_code,
                        'changes': file_changes
                    })

                    if modified and not dry_run:
                        self.backup_config(config_path)
                        self.save_config(config_path, config)
                        results['files_modified'] += 1

            except Exception as e:
                logger.error(f"Error processing {config_path}: {e}")

        return results

    def enable_category(
        self,
        category: str,
        states: List[str] = None,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Enable a data category across config files.

        Args:
            category: Category name to enable
            states: List of state codes (None = all)
            dry_run: If True, don't actually make changes

        Returns:
            Summary of changes
        """
        results = {
            'files_checked': 0,
            'files_modified': 0,
            'states_updated': [],
            'dry_run': dry_run
        }

        for config_path in self.list_configs():
            state_code = config_path.stem.upper()

            if states and state_code not in states:
                continue

            results['files_checked'] += 1

            try:
                config = self.load_config(config_path)

                # Ensure categories section exists
                if 'categories' not in config:
                    config['categories'] = {}

                # Enable category if not already enabled
                if category not in config['categories'] or not config['categories'].get(category, {}).get('enabled', False):
                    if not dry_run:
                        self.backup_config(config_path)
                        config['categories'][category] = {
                            'enabled': True,
                            'added_at': datetime.utcnow().isoformat()
                        }
                        self.save_config(config_path, config)
                        results['files_modified'] += 1

                    results['states_updated'].append(state_code)

            except Exception as e:
                logger.error(f"Error processing {config_path}: {e}")

        return results

    def disable_category(
        self,
        category: str,
        states: List[str] = None,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Disable a data category across config files.

        Args:
            category: Category name to disable
            states: List of state codes (None = all)
            dry_run: If True, don't actually make changes

        Returns:
            Summary of changes
        """
        results = {
            'files_checked': 0,
            'files_modified': 0,
            'states_updated': [],
            'dry_run': dry_run
        }

        for config_path in self.list_configs():
            state_code = config_path.stem.upper()

            if states and state_code not in states:
                continue

            results['files_checked'] += 1

            try:
                config = self.load_config(config_path)

                if 'categories' in config and category in config['categories']:
                    if config['categories'][category].get('enabled', False):
                        if not dry_run:
                            self.backup_config(config_path)
                            config['categories'][category]['enabled'] = False
                            config['categories'][category]['disabled_at'] = datetime.utcnow().isoformat()
                            self.save_config(config_path, config)
                            results['files_modified'] += 1

                        results['states_updated'].append(state_code)

            except Exception as e:
                logger.error(f"Error processing {config_path}: {e}")

        return results

    def add_endpoint(
        self,
        endpoint_name: str,
        endpoint_config: Dict[str, Any],
        states: List[str] = None,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Add a new endpoint to config files.

        Args:
            endpoint_name: Name for the new endpoint
            endpoint_config: Endpoint configuration dict
            states: List of state codes (None = all)
            dry_run: If True, don't actually make changes

        Returns:
            Summary of changes
        """
        results = {
            'files_checked': 0,
            'files_modified': 0,
            'states_updated': [],
            'dry_run': dry_run
        }

        for config_path in self.list_configs():
            state_code = config_path.stem.upper()

            if states and state_code not in states:
                continue

            results['files_checked'] += 1

            try:
                config = self.load_config(config_path)

                if 'endpoints' not in config:
                    config['endpoints'] = {}

                if endpoint_name not in config['endpoints']:
                    if not dry_run:
                        self.backup_config(config_path)
                        config['endpoints'][endpoint_name] = endpoint_config
                        self.save_config(config_path, config)
                        results['files_modified'] += 1

                    results['states_updated'].append(state_code)

            except Exception as e:
                logger.error(f"Error processing {config_path}: {e}")

        return results

    def apply_transform(
        self,
        transform_fn: Callable[[Dict[str, Any], str], Dict[str, Any]],
        states: List[str] = None,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Apply a custom transformation function to configs.

        Args:
            transform_fn: Function that takes (config, state_code) and returns modified config
            states: List of state codes (None = all)
            dry_run: If True, don't actually make changes

        Returns:
            Summary of changes
        """
        results = {
            'files_checked': 0,
            'files_modified': 0,
            'states_processed': [],
            'dry_run': dry_run
        }

        for config_path in self.list_configs():
            state_code = config_path.stem.upper()

            if states and state_code not in states:
                continue

            results['files_checked'] += 1

            try:
                config = self.load_config(config_path)
                original = json.dumps(config, sort_keys=True)

                # Apply transformation
                modified_config = transform_fn(config, state_code)
                modified = json.dumps(modified_config, sort_keys=True)

                if original != modified:
                    if not dry_run:
                        self.backup_config(config_path)
                        self.save_config(config_path, modified_config)
                        results['files_modified'] += 1

                    results['states_processed'].append(state_code)

            except Exception as e:
                logger.error(f"Error processing {config_path}: {e}")

        return results

    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get summary of all config files.

        Returns:
            Summary including counts, endpoints, categories per state
        """
        summary = {
            'total_configs': 0,
            'states': [],
            'by_state': {},
            'all_endpoints': set(),
            'all_categories': set()
        }

        for config_path in self.list_configs():
            state_code = config_path.stem.upper()
            summary['total_configs'] += 1
            summary['states'].append(state_code)

            try:
                config = self.load_config(config_path)

                state_info = {
                    'endpoints': list(config.get('endpoints', {}).keys()),
                    'categories': list(config.get('categories', {}).keys()),
                    'has_base_url': 'base_url' in config
                }

                summary['by_state'][state_code] = state_info
                summary['all_endpoints'].update(state_info['endpoints'])
                summary['all_categories'].update(state_info['categories'])

            except Exception as e:
                logger.error(f"Error reading {config_path}: {e}")

        summary['all_endpoints'] = sorted(list(summary['all_endpoints']))
        summary['all_categories'] = sorted(list(summary['all_categories']))

        return summary
