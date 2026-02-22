# api/main.py
# Urban Intelligence Framework - FastAPI Application
# RESTfull API for model serving and data access

"""
FastAPI application for the Urban Intelligence Framework.

This module provides a production-ready REST API with:
    - Price prediction endpoints
    - City data queries
    - Model management
    - Health checks and monitoring

Run with:
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import logging
import os
import pickle
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_settings
from src.data import DataService, DataStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
