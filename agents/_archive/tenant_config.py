"""
Tenant Configuration Loader
Maps inbound phone numbers to tenant configs (location_id, business name, etc.)
for multi-tenant routing.
"""

import json
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("tenant-config")


class TenantConfig:
    """Loads tenants.json and resolves phone numbers to tenant context."""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), "tenants.json")
        self.config_path = config_path
        self._tenants: Dict[str, Dict[str, Any]] = {}
        self._default: Dict[str, Any] = {}
        self.load()

    def load(self):
        """Load tenant config from disk."""
        try:
            with open(self.config_path, "r") as f:
                config = json.load(f)
            self._tenants = config.get("tenants", {})
            self._default = config.get("default_tenant", {})
            logger.info(f"Loaded tenant config: {len(self._tenants)} tenant(s)")
        except FileNotFoundError:
            logger.warning(f"Tenant config not found at {self.config_path}, using defaults")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in tenant config: {e}")

    def resolve(self, called_number: Optional[str]) -> Dict[str, Any]:
        """
        Resolve tenant config for a called phone number.
        Returns dict with at least: location_id, business_name
        """
        tenant = None
        if called_number:
            normalized = called_number.strip()
            if not normalized.startswith("+"):
                normalized = "+" + normalized
            tenant = self._tenants.get(normalized)

        if tenant:
            logger.info(f"Tenant matched for {called_number}: {tenant.get('business_name')}")
            result = dict(tenant)
        else:
            logger.info(f"No tenant for {called_number}, using default")
            result = dict(self._default)

        # Resolve ENV: references for all string fields (e.g. "ENV:DEFAULT_GHL_LOCATION_ID")
        for key, value in list(result.items()):
            if isinstance(value, str) and value.startswith("ENV:"):
                result[key] = os.getenv(value[4:])

        # Final fallback chain
        if not result.get("location_id"):
            result["location_id"] = (
                os.getenv("DEFAULT_GHL_LOCATION_ID") or os.getenv("GHL_LOCATION_ID")
            )

        if not result.get("business_name"):
            result["business_name"] = "Our Business"

        return result
