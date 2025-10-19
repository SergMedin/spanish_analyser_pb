"""
Setup script для модуля spanish_analyser
"""

from setuptools import setup, find_packages
from pathlib import Path

# Читаем README для описания
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

setup(
    name="spanish_analyser",
    version="0.1.0",
    author="Sergey",
    description="Модуль для анализа испанского языка с интеграцией Anki",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Education :: Language",
        "Topic :: Text Processing :: Linguistic",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pandas>=1.5.0",
        "numpy>=1.21.0",
        "beautifulsoup4>=4.11.0",
        "lxml>=4.9.0",
        "openpyxl>=3.0.0",
        "xlrd>=2.0.0",
        "python-dotenv>=0.19.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=22.0",
            "flake8>=4.0",
        ],
        "anki": [
            "anki>=2.1.0",
        ],
        "nlp": [
            "spacy>=3.5.0",
        ],
        "openai": [
            "openai>=1.0.0",
        ],
    },
    # Консольные скрипты отключены: в пакете нет исполняемого модуля
    # с путём spanish_analyser.main. Запуск утилит осуществляется через
    # files в tools/ или через Makefile цели (run/scrape/analyze).
    include_package_data=True,
    zip_safe=False,
)
