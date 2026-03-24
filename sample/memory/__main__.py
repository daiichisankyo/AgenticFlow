"""Allow running as: python -m memory"""

import asyncio

from .cli import main

asyncio.run(main())
