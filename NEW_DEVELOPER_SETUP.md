# New Developer Setup Guide

## Prerequisites

- **OS**: Windows 10/11
- **Python**: 3.10 or higher
- **Docker Access**: For PostgreSQL and Neo4j databases
- **Ollama**: Installed and running

## Step-by-Step Setup

1.  **Clone the Repository**

    ```powershell
    git clone <repository-url>
    cd <repository-folder>
    ```

2.  **Run the Automated Setup Script**
    This script creates a virtual environment, installs Python dependencies, and pulls necessary Ollama models.

    ```powershell
    .\setup_env.bat
    ```

3.  **Start Database Services**
    Ensure Docker is running, then start the containers:

    ```powershell
    docker-compose up -d
    ```

4.  **Initialize the Database**
    Create the necessary tables and schema:

    ```powershell
    .\venv312\Scripts\python scripts/init_db.py
    ```

5.  **Verify the System**
    Run the API to ensure everything is connected:
    ```powershell
    .\run_api.bat
    ```
    Visit `http://localhost:8000/docs` to see the API Swagger UI.

## Common Issues

- **Missing DLLs**: If you get import errors for `torch` or `pydantic`, ensure the virtual environment is activated.
- **Database Connection**: Check Docker logs (`docker-compose logs postgres`) if valid connection fails.

## Important Note on Copying/Moving the Project

If you copy this project folder to a new location (even on the same machine):

1.  **Virtual Environments**: You MUST delete `venv` and `venv312` and run `setup_env.bat` again. They are not portable.
2.  **Database State (Critical)**:
    - **PostgreSQL**: Docker volumes are based on the folder name. A copy will start with an **EMPTY** vector database.
    - **Neo4j**: If running locally (default), it shares the **SAME** graph database.
    - **Risk**: This creates a mismatch (empty vectors vs. populated graph). You should reset the databases or use distinct ports in `.env` for the new copy.
