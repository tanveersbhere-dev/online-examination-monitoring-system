import unittest
from pathlib import Path

from ai_engine.config.config import load_config, SystemConfig
from ai_engine.core.exceptions import ConfigurationError

class TestConfig(unittest.TestCase):
    def test_load_default_config(self) -> None:
        """Verifies that the default system configuration loads without errors."""
        try:
            config = load_config()
            self.assertIsInstance(config, SystemConfig)
            self.assertEqual(config.camera.width, 640)
            self.assertEqual(config.camera.height, 480)
            self.assertIn("cell phone", config.objects.disallowed_objects)
        except ConfigurationError as e:
            self.fail(f"Configuration failed to load: {e}")

    def test_load_invalid_config_path(self) -> None:
        """Verifies that an invalid config directory raises a ConfigurationError."""
        with self.assertRaises(ConfigurationError):
            load_config(config_dir=Path("/non_existent_directory"))

    def test_config_validation(self) -> None:
        """Verifies that invalid configuration values trigger ConfigurationError."""
        from ai_engine.config.config import validate_config
        
        # Helper to generate a baseline valid SystemConfig
        config = load_config()
        
        # Test invalid camera width
        config.camera.width = -1
        with self.assertRaises(ConfigurationError):
            validate_config(config)
        config.camera.width = 640
        
        # Test invalid camera height
        config.camera.height = 0
        with self.assertRaises(ConfigurationError):
            validate_config(config)
        config.camera.height = 480
        
        # Test invalid camera fps
        config.camera.fps = -5.0
        with self.assertRaises(ConfigurationError):
            validate_config(config)
        config.camera.fps = 30.0

        # Test invalid buffer size
        config.camera.buffer_size = 0
        with self.assertRaises(ConfigurationError):
            validate_config(config)
        config.camera.buffer_size = 10
        
        # Test invalid event bus queue size
        config.event_bus.queue_size = -10
        with self.assertRaises(ConfigurationError):
            validate_config(config)
        config.event_bus.queue_size = 100

        # Test invalid log level
        config.logging.level = "INVALID_LEVEL"
        with self.assertRaises(ConfigurationError):
            validate_config(config)
        config.logging.level = "INFO"

