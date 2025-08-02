"""
Setup script for News Agent package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    requirements = [line.strip() for line in requirements_path.read_text().splitlines() 
                   if line.strip() and not line.startswith("#")]

setup(
    name="news-agent",
    version="1.0.0",
    author="News Agent Team",
    author_email="team@newsagent.com",
    description="Automated news aggregation and notification system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/news-agent",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Communications",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content :: News/Diary",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-mock>=3.12.0",
            "black>=23.11.0",
            "flake8>=6.1.0",
            "mypy>=1.7.1",
            "pre-commit>=3.6.0",
        ],
        "web": [
            "fastapi>=0.104.1",
            "uvicorn>=0.24.0",
            "jinja2>=3.1.2",
        ],
    },
    entry_points={
        "console_scripts": [
            "news-agent=cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml", "*.json"],
    },
    keywords="news, aggregation, ai, whatsapp, notifications, rss, trends",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/news-agent/issues",
        "Source": "https://github.com/yourusername/news-agent",
        "Documentation": "https://github.com/yourusername/news-agent#readme",
    },
) 