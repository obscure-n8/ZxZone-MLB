# ZxZone-MLB Bot Package
# Powered By Zonexus Hub

__version__ = "2.0.0"
__author__ = "Zonexus Hub"
__license__ = "MIT"

import os
import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

# Import core modules
from bot.config import Config
from bot.core import *
from bot.helpers import *
from bot.modules import *
from bot.database import *
from bot.plugins import *

def get_version():
    return __version__

def get_bot_info():
    return {
        'name': 'ZxZone-MLB',
        'version': __version__,
        'author': __author__,
        'license': __license__,
        'powered_by': 'Zonexus Hub'
    }
