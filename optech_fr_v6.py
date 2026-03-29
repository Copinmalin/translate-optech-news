#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
import optech_fr_v5

optech_fr_v5.PREFERENCES_PATH = Path("preferences_fr_v2.yaml")

if __name__ == "__main__":
    optech_fr_v5.main()
