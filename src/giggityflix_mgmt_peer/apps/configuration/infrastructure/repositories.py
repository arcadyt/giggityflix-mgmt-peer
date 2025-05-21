"""Repository implementations for configuration management."""
import json
from typing import Dict, Optional

from django.utils import timezone

from giggityflix_mgmt_peer.apps.configuration.domain.models import ConfigurationValue
from giggityflix_mgmt_peer.apps.configuration.infrastructure.orm import Configuration as ConfigurationOrm


class DjangoConfigurationRepository:
    """Django ORM-based repository for configuration."""
    
    def get(self, key: str) -> Optional[ConfigurationValue]:
        """
        Get a configuration value by key.
        
        Args:
            key: The configuration key
            
        Returns:
            Configuration value or None if not found
        """
        try:
            orm_config = ConfigurationOrm.objects.get(key=key)
            return self._orm_to_domain(orm_config)
        except ConfigurationOrm.DoesNotExist:
            return None
    
    def save(self, config: ConfigurationValue) -> bool:
        """
        Save a configuration value.
        
        Args:
            config: The configuration value to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            orm_config, created = ConfigurationOrm.objects.update_or_create(
                key=config.key,
                defaults={
                    'value': config._value,
                    'default_value': config._default_value,
                    'value_type': config.value_type,
                    'description': config.description,
                    'is_env_overridable': config.is_env_overridable,
                    'env_variable': config.env_variable
                }
            )
            return True
        except Exception:
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete a configuration value.
        
        Args:
            key: The configuration key
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            result = ConfigurationOrm.objects.filter(key=key).delete()
            return result[0] > 0
        except Exception:
            return False
    
    def get_all(self) -> Dict[str, ConfigurationValue]:
        """
        Get all configuration values.
        
        Returns:
            Dictionary of configuration keys and values
        """
        result = {}
        orm_configs = ConfigurationOrm.objects.all()
        
        for orm_config in orm_configs:
            domain_config = self._orm_to_domain(orm_config)
            result[domain_config.key] = domain_config
        
        return result
    
    def _orm_to_domain(self, orm_config: ConfigurationOrm) -> ConfigurationValue:
        """Convert ORM model to domain model."""
        return ConfigurationValue(
            key=orm_config.key,
            value=orm_config.value,
            default_value=orm_config.default_value,
            value_type=orm_config.value_type,
            description=orm_config.description,
            is_env_overridable=orm_config.is_env_overridable,
            env_variable=orm_config.env_variable
        )


# Singleton instance
_configuration_repository = None


def get_configuration_repository() -> DjangoConfigurationRepository:
    """
    Get or create the configuration repository singleton.
    
    Returns:
        DjangoConfigurationRepository instance
    """
    global _configuration_repository
    if _configuration_repository is None:
        _configuration_repository = DjangoConfigurationRepository()
    return _configuration_repository
