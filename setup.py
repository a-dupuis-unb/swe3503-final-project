from setuptools import setup, find_packages

setup(
    name="final_project",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Flask',
        'Flask-SQLAlchemy',
        'Flask-Migrate',
        'Flask-Login',
        'cryptography',
    ],
    python_requires='>=3.6',
    description="SWE3503 Final Project - Expense Tracking Application",
    author="",
    author_email="",
    url="https://github.com/a-dupuis-unb/swe3503-final-project",
)

