# mew/tasks/__init__.py
from .base_task import BaseTask
from .auto_mew import AutoMewTask
from .fishing import FishingTask
from .collect import CollectTask

__all__ = ["BaseTask", "AutoMewTask", "FishingTask", "CollectTask"]