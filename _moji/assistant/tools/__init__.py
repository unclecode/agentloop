import os
import importlib
from typing import Dict, Any, Callable

ALL_TOOLS: Dict[str, Callable] = {}
ALL_SCHEMAS: Dict[str, Dict[str, Any]] = {}

# Dynamically import all tools
for filename in os.listdir(os.path.dirname(__file__)):
    if filename.endswith('.py') and filename != '__init__.py':
        module_name = filename[:-3]
        module = importlib.import_module(f'.{module_name}', package='assistant.tools')
        
        if hasattr(module, 'TOOLS'):
            ALL_TOOLS.update(module.TOOLS)
        
        if hasattr(module, 'TOOL_SCHEMA'):
            ALL_SCHEMAS[module.TOOL_SCHEMA['name']] = module.TOOL_SCHEMA
        elif hasattr(module, 'TOOL_SCHEMAS'):
            ALL_SCHEMAS.update(module.TOOL_SCHEMAS)
            

