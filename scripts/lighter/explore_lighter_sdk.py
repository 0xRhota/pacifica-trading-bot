#!/usr/bin/env python3
"""Quick SDK exploration"""

import lighter

print("Lighter SDK attributes:")
print([attr for attr in dir(lighter) if not attr.startswith('_')])
