# Giggityflix Management Peer Service

Resource management microservice for the Giggityflix media streaming platform with physical drive detection, configuration management, and resource pooling.

## Architecture

- **Domain-Driven Design** - Structured around domain concepts with clear boundaries
- **Django ORM** - For data persistence and REST API framework
- **Strategy Pattern** - For OS-specific drive detection implementations 
- **Resource Pooling** - Efficient CPU and IO management with concurrency controls

## Key Components

### Drive Detection

- Automatic physical drive and partition detection for Windows, Linux, and macOS
- Cross-platform abstraction with strategy pattern for OS-specific implementations
- Django ORM persistence with RESTful API

### Configuration Service

- Type-aware configuration system (string, integer, boolean, JSON, list)
- Environment variable overrides
- Signal-based cache invalidation
- RESTful configuration management API

### Resource Management

- Intelligent CPU/IO task handling with automatic executor selection
- Per-drive IO concurrency limits with dynamic scaling
- Decorators for effortless resource management:
  - `@io_bound()` - For filesystem and network operations
  - `@cpu_bound()` - For compute-intensive tasks

## Installation

```bash
# Clone repository
git clone https://github.com/giggityflix/giggityflix-mgmt-peer.git
cd giggityflix-mgmt-peer

# Install dependencies
poetry install

# Run migrations
poetry run python src/giggityflix_mgmt_peer/manage.py migrate
```

## Usage

### Starting the Service

```bash
# Start the Django server
poetry run python src/giggityflix_mgmt_peer/manage.py runserver 0.0.0.0:8000
```

### API Endpoints

```
# Drive management
GET    /api/drives/                # List all detected drives
GET    /api/drives/{id}/           # Get drive details
POST   /api/drives/refresh/        # Trigger drive detection

# Partition management
GET    /api/partitions/            # List all partitions
GET    /api/partitions/{id}/       # Get partition details

# Configuration management
GET    /api/configurations/        # List all configurations
GET    /api/configurations/{key}/  # Get configuration
POST   /api/configurations/        # Create configuration
PUT    /api/configurations/{key}/  # Update configuration
PATCH  /api/configurations/{key}/  # Partial update
```

### API Examples

```powershell
# List detected drives
Invoke-WebRequest -Method GET -Uri "localhost:8000/api/drives/" | Select-Object -ExpandProperty Content

# Get configurations
Invoke-WebRequest -Method GET -Uri "localhost:8000/api/configurations/" | Select-Object -ExpandProperty Content

# Refresh drive detection
Invoke-WebRequest -Method POST -Uri "localhost:8000/api/drives/refresh/" | Select-Object -ExpandProperty Content
```

## Development

### Command-line Utilities

```bash
# Detect drives (updates database)
poetry run python src/giggityflix_mgmt_peer/manage.py detect_drives

# Run tests
poetry run pytest

# Create migrations
poetry run python src/giggityflix_mgmt_peer/manage.py makemigrations
```

### Project Structure

```
src/giggityflix_mgmt_peer/
├── apps/                              # Django applications
│   ├── configuration/                 # Configuration service
│   └── drive_detection/               # Drive detection service
│       ├── application/               # Application services
│       ├── domain/                    # Domain models and interfaces
│       ├── infrastructure/            # Repositories and ORM models
│       ├── interfaces/                # API endpoints
│       └── strategies/                # OS-specific implementations
├── core/                              # Core framework components
│   └── resource_pool/                 # Resource management
└── manage.py                          # Django management script
```
