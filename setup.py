from setuptools import setup, find_packages

setup(
    name="datagod",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "alembic==1.17.2",
        "psycopg2-binary==2.9.11",
        "sqlalchemy==2.0.23",
        "mako==1.3.10",
        "markupsafe==3.0.3",
        "pydantic==2.12.5",
        "pydantic-settings==2.12.0",
        "python-dotenv==1.0.0",
    ],
)
