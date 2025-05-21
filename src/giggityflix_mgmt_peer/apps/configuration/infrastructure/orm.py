"""ORM models for configuration management."""
from django.db import models


class Configuration(models.Model):
    """Django ORM model for storing configuration properties."""
    
    # Type choices for proper conversion
    TYPE_STRING = 'string'
    TYPE_INTEGER = 'integer'
    TYPE_FLOAT = 'float'
    TYPE_BOOLEAN = 'boolean'
    TYPE_JSON = 'json'
    TYPE_LIST = 'list'

    TYPE_CHOICES = [
        (TYPE_STRING, 'String'),
        (TYPE_INTEGER, 'Integer'),
        (TYPE_FLOAT, 'Float'),
        (TYPE_BOOLEAN, 'Boolean'),
        (TYPE_JSON, 'JSON'),
        (TYPE_LIST, 'List'),
    ]

    key = models.CharField(max_length=255, primary_key=True,
                           help_text="Configuration property key")
    value = models.TextField(null=True, blank=True,
                             help_text="Current value of the configuration property")
    default_value = models.TextField(null=True, blank=True,
                                     help_text="Default value if not specified")
    value_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_STRING,
                                  help_text="Type of the configuration value")
    description = models.TextField(null=True, blank=True,
                                   help_text="Description of the configuration property")
    is_env_overridable = models.BooleanField(default=True,
                                             help_text="Whether environment variables can override this configuration")
    env_variable = models.CharField(max_length=255, null=True, blank=True,
                                    help_text="Environment variable name to use for override")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'configuration'
        ordering = ['key']
        verbose_name = 'Configuration'
        verbose_name_plural = 'Configurations'

    def __str__(self):
        return f"{self.key}: {self.value}"
