#!/usr/bin/env python3
"""
Script to start the Care Companion backend server
"""

import uvicorn
import os
import sys

if __name__ == "__main__":
    # Add the app directory to the Python path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

    # Start the FastAPI server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["./app"],
        log_level="info"
    )