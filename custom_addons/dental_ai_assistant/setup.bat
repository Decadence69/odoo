@echo off
REM Setup script for Dental AI Assistant - Windows Version
REM This script helps you set up the complete RAG system for your Odoo 18 website

echo ===================================
echo   Dental AI Assistant Setup
echo ===================================
echo.

REM Check if running from correct directory
if not exist "setup.bat" (
    echo Please run this script from the dental_ai_assistant directory
    pause
    exit /b 1
)

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo X Python is required but not installed.
    echo Please install Python from https://python.org
    pause
    exit /b 1
)
echo ✓ Python found

REM Check pip installation
pip --version >nul 2>&1
if errorlevel 1 (
    echo X pip is required but not installed.
    echo Please install pip or reinstall Python with pip included
    pause
    exit /b 1
)
echo ✓ pip found

REM Install Python dependencies
echo.
echo Installing Python dependencies...
pip install google-generativeai sentence-transformers chromadb numpy pandas

if errorlevel 1 (
    echo X Failed to install dependencies
    pause
    exit /b 1
)
echo ✓ Dependencies installed successfully

REM Create directory structure
echo.
echo Creating directory structure...
if not exist "models" mkdir models
if not exist "controllers" mkdir controllers
if not exist "views" mkdir views
if not exist "static" mkdir static
if not exist "static\src" mkdir static\src
if not exist "static\src\js" mkdir static\src\js
if not exist "static\src\css" mkdir static\src\css
if not exist "security" mkdir security
if not exist "data" mkdir data

echo ✓ Directory structure created

REM Create __init__.py files (Windows equivalent of touch)
echo.
echo Creating Python module files...
echo. > __init__.py
echo. > models\__init__.py
echo. > controllers\__init__.py

echo ✓ Python module files created

REM Create the RAG system file
echo.
echo Creating RAG system file...
(
echo # This file should contain the DentalRAGSystem class
echo # Copy the complete RAG implementation here
echo.
echo import json
echo import os
echo import pickle
echo from typing import List, Dict, Any
echo import numpy as np
echo import pandas as pd
echo from sentence_transformers import SentenceTransformer
echo import chromadb
echo from chromadb.config import Settings
echo import google.generativeai as genai
echo.
echo class DentalRAGSystem:
echo     def __init__^(self, api_key: str, persist_directory: str = "./dental_knowledge_db"^):
echo         """Initialize the Dental RAG System"""
echo         self.api_key = api_key
echo         self.persist_directory = persist_directory
echo         self.embedding_model = SentenceTransformer^('all-MiniLM-L6-v2'^)
echo         
echo         # Initialize Gemini
echo         genai.configure^(api_key=api_key^)
echo         self.gemini_model = genai.GenerativeModel^('gemini-pro'^)
echo         
echo         # Initialize ChromaDB
echo         self.client = chromadb.Client^(Settings^(
echo             chroma_db_impl="duckdb+parquet",
echo             persist_directory=persist_directory
echo         ^^)^)
echo         
echo         self.collection = None
echo.
echo     # TODO: Add the complete implementation from the RAG system artifact
echo     # This is a placeholder - you need to copy the full implementation
) > models\dental_rag_system.py

echo ✓ RAG system file created

REM Create test data file
echo.
echo Creating test data file...
(
echo {"dental_procedures": ["Cavity Preparation", "Crown Preparation"], "burs_tools": ["Round diamond burs"], "bur_usage": {"Cavity Preparation": "Precise cutting action for removing decayed tooth material", "Crown Preparation": "Shaping the tooth accurately for crown preparation"}, "advantages_insights": ["Precision and efficiency", "Preserves healthy tooth structure"], "title": "Test Blog 1"}
) > test_blogs.jsonl

echo ✓ Test data file created

REM Create configuration template
echo.
echo Creating configuration template...
(
echo # Configuration Template for Dental AI Assistant
echo # Copy this file to config.py and fill in your details
echo.
echo # Gemini API Configuration
echo GEMINI_API_KEY = "your-gemini-api-key-here"
echo.
echo # File Paths
echo JSONL_BLOG_FILE = "path/to/your/blog/data.jsonl"
echo KNOWLEDGE_BASE_PATH = "./dental_knowledge_db"
echo.
echo # Test the setup
echo def test_setup^(^):
echo     print^("Testing Gemini API connection..."^)
echo     import google.generativeai as genai
echo     
echo     genai.configure^(api_key=GEMINI_API_KEY^)
echo     model = genai.GenerativeModel^('gemini-pro'^)
echo     
echo     try:
echo         response = model.generate_content^("Hello, this is a test connection."^)
echo         print^("✓ Gemini API connection successful!"^)
echo         return True
echo     except Exception as e:
echo         print^(f"X Gemini API connection failed: {e}"^)
echo         return False
echo.
echo if __name__ == "__main__":
echo     test_setup^(^)
) > config_template.py

echo ✓ Configuration template created

REM Create Windows-specific installation instructions
echo.
echo Creating installation instructions...
(
echo # Dental AI Assistant Installation Guide - Windows
echo.
echo ## Step 1: Get Gemini API Key
echo 1. Go to [Google AI Studio]^(https://aistudio.google.com/^)
echo 2. Sign in with your Google account
echo 3. Create a new API key
echo 4. Copy the API key
echo.
echo ## Step 2: Configure the System
echo 1. Copy `config_template.py` to `config.py`
echo 2. Edit `config.py` and add your Gemini API key
echo 3. Update the path to your JSONL blog file
echo 4. Test the connection: `python config.py`
echo.
echo ## Step 3: Build Knowledge Base
echo ```python
echo from models.dental_rag_system import DentalRAGSystem
echo.
echo # Initialize system
echo rag_system = DentalRAGSystem^("your-api-key"^)
echo.
echo # Build knowledge base
echo rag_system.build_knowledge_base^("path/to/your/blogs.jsonl"^)
echo ```
echo.
echo ## Step 4: Install Odoo Module
echo 1. Copy this entire directory to your Odoo addons folder
echo 2. Update apps list in Odoo
echo 3. Install "Dental AI Assistant" module
echo 4. Configure API key in Settings ^> Dental AI Configuration
echo.
echo ## Step 5: Test the System
echo 1. Go to Dental AI Assistant ^> Ask Dental AI
echo 2. Enter a query like "What burs for crown preparation?"
echo 3. Get AI-powered recommendations!
echo.
echo ## Windows-Specific Notes
echo - Use backslashes ^(\^) or forward slashes ^(/^) in file paths
echo - Example: "C:\path\to\your\blog\data.jsonl" or "C:/path/to/your/blog/data.jsonl"
echo - Make sure Python is added to your PATH environment variable
echo - You may need to run Command Prompt as Administrator for some operations
echo.
echo ## Troubleshooting
echo - Make sure all Python dependencies are installed
echo - Check that your API key is valid
echo - Ensure JSONL file path uses correct Windows path format
echo - Check Odoo logs for any errors
echo - On Windows, use `python` instead of `python3` if needed
) > INSTALLATION_WINDOWS.md

echo ✓ Installation instructions created

REM Create Windows-compatible test script
echo.
echo Creating test script...
(
echo # Quick test script for the Dental RAG system - Windows Version
echo """
echo Quick test script for the Dental RAG system
echo """
echo.
echo def test_basic_functionality^(^):
echo     print^("Testing basic RAG functionality..."^)
echo     
echo     try:
echo         from models.dental_rag_system import DentalRAGSystem
echo         print^("✓ RAG system imported successfully"^)
echo         
echo         # Test with dummy API key ^(will fail but tests import^)
echo         rag = DentalRAGSystem^("dummy-key"^)
echo         print^("✓ RAG system initialized"^)
echo         
echo         # Test JSONL processing
echo         chunks = rag.process_jsonl_blogs^("test_blogs.jsonl"^)
echo         print^(f"✓ Processed {len^(chunks^)} chunks from test data"^)
echo         
echo         return True
echo         
echo     except Exception as e:
echo         print^(f"X Test failed: {e}"^)
echo         return False
echo.
echo if __name__ == "__main__":
echo     test_basic_functionality^(^)
) > quick_test.py

echo ✓ Test script created

REM Create Windows batch file for easy testing
echo.
echo Creating quick test batch file...
(
echo @echo off
echo echo Testing Dental AI System...
echo python quick_test.py
echo pause
) > test_system.bat

echo ✓ Test batch file created

echo.
echo 🎉 Setup completed successfully!
echo.
echo Next steps:
echo 1. Get your Gemini API key from https://aistudio.google.com/
echo 2. Copy config_template.py to config.py and add your API key
echo 3. Update the JSONL file path in config.py ^(use Windows path format^)
echo 4. Run: python quick_test.py
echo 5. Install the Odoo module
echo.
echo 📚 See INSTALLATION_WINDOWS.md for detailed instructions
echo.
echo Files created:
echo   - models\dental_rag_system.py ^(RAG system implementation^)
echo   - config_template.py ^(configuration template^)
echo   - test_blogs.jsonl ^(sample test data^)
echo   - quick_test.py ^(test script^)
echo   - test_system.bat ^(easy test runner^)
echo   - INSTALLATION_WINDOWS.md ^(detailed Windows instructions^)
echo.
echo Press any key to continue...
pause