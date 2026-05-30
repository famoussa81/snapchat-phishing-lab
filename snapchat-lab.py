#!/usr/bin/env python
"""Wrapper that calls cli.py from the project root."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cli import cli
cli()
