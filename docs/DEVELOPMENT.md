# Development Guide

## Getting Started

### Prerequisites
```bash
python --version  # 3.9+
pip --version
git --version  # optional
```

### Initial Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run setup
python setup.py

# Test the installation
python -c "import mcp; print('MCP installed')"
```

## Project Structure

```
ClaudesPathOfExile2EnhancementService/
├── src/
│   ├── mcp_server.py       # Main MCP server
│   ├── config.py           # Configuration management
│   ├── api/                # API clients and utilities
│   │   ├── poe_api.py      # PoE official API
│   │   ├── rate_limiter.py # Rate limiting
│   │   └── cache_manager.py# Caching system
│   ├── database/           # Database layer
│   │   ├── models.py       # SQLAlchemy models
│   │   └── manager.py      # Database operations
│   ├── calculator/         # Build calculations
│   │   └── build_scorer.py # Build quality scoring
│   ├── optimizer/          # Optimization engines
│   │   ├── gear_optimizer.py
│   │   ├── passive_optimizer.py
│   │   └── skill_optimizer.py
│   ├── ai/                 # AI components
│   │   ├── query_handler.py
│   │   └── recommendation_engine.py
│   └── pob/                # Path of Building integration
│       ├── importer.py
│       └── exporter.py
├── data/                   # SQLite databases
├── cache/                  # Cache storage
├── logs/                   # Log files
├── scripts/                # Utility scripts
├── tests/                  # Test suite
├── web/                    # Web interface (future)
├── launch.py               # Quick launcher
├── setup.py                # Setup script
├── requirements.txt        # Python dependencies
├── config.yaml             # Configuration file
├── .env                    # Environment variables
└── README.md               # Main documentation
```

## Development Workflow

### 1. Making Changes

```bash
# Create a feature branch (if using git)
git checkout -b feature-name

# Make your changes
# Edit files in src/

# Test your changes
python tests/test_your_feature.py

# Run the server
python launch.py
```

### 2. Adding a New MCP Tool

**Example**: Adding a "damage_breakdown" tool

```python
# In src/mcp_server.py

# 1. Add tool definition in _register_tools()
types.Tool(
    name="damage_breakdown",
    description="Get detailed damage breakdown for a skill",
    inputSchema={
        "type": "object",
        "properties": {
            "skill_name": {
                "type": "string",
                "description": "Name of the skill to analyze"
            }
        },
        "required": ["skill_name"]
    }
)

# 2. Add handler in handle_call_tool()
elif name == "damage_breakdown":
    return await self._handle_damage_breakdown(arguments)

# 3. Implement the handler
async def _handle_damage_breakdown(self, args: dict) -> List[types.TextContent]:
    """Handle damage breakdown request"""
    skill_name = args["skill_name"]

    # Your implementation here
    breakdown = await self.calculate_damage(skill_name)

    return [types.TextContent(
        type="text",
        text=f"Damage breakdown for {skill_name}:\n{breakdown}"
    )]
```

### 3. Adding a New Database Model

```python
# In src/database/models.py

class NewModel(Base):
    """Description of the model"""
    __tablename__ = "new_table"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, index=True)
    data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

# Then run migrations
alembic revision --autogenerate -m "Add new model"
alembic upgrade head
```

### 4. Adding an API Client

```python
# In src/api/new_api.py

import httpx
from ..config import settings
from .rate_limiter import RateLimiter

class NewAPIClient:
    """Client for New API"""

    def __init__(self, rate_limiter: RateLimiter = None):
        self.base_url = settings.NEW_API_URL
        self.rate_limiter = rate_limiter or RateLimiter(rate_limit=30)
        self.client = httpx.AsyncClient()

    async def fetch_data(self, endpoint: str):
        """Fetch data from API"""
        await self.rate_limiter.acquire()

        response = await self.client.get(f"{self.base_url}/{endpoint}")
        return response.json()
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_api.py

# Run with coverage
pytest --cov=src tests/

# Run with verbose output
pytest -v
```

### Writing Tests

```python
# tests/test_calculator.py

import pytest
from src.calculator.build_scorer import BuildScorer

@pytest.mark.asyncio
async def test_build_scorer():
    """Test build scoring"""
    scorer = BuildScorer(None)  # Mock db_manager

    character_data = {
        "name": "TestChar",
        "class": "Witch",
        "level": 70
    }

    result = await scorer.analyze_build(character_data)

    assert "overall_score" in result
    assert 0.0 <= result["overall_score"] <= 1.0
    assert result["tier"] in ["S", "A", "B", "C", "D"]
```

## Configuration

### Environment Variables

```bash
# .env file
ANTHROPIC_API_KEY=your_key
DEBUG=true
LOG_LEVEL=DEBUG
```

### YAML Configuration

```yaml
# config.yaml
server:
  port: 8080
  workers: 4

cache:
  enabled: true
  ttl: 3600
```

### Accessing Config

```python
from src.config import settings

api_key = settings.ANTHROPIC_API_KEY
debug_mode = settings.DEBUG
```

## Database Management

### Migrations

```bash
# Create a migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# View history
alembic history
```

### Direct Database Access

```python
from src.database.manager import DatabaseManager

async def query_items():
    db = DatabaseManager()
    await db.initialize()

    items = await db.search_items("Unique Sword")
    print(items)

    await db.close()
```

## Debugging

### Enable Debug Logging

```python
# In .env
DEBUG=true
LOG_LEVEL=DEBUG
```

### View Logs

```bash
# Tail logs
tail -f logs/poe2_optimizer.log

# Windows
Get-Content logs/poe2_optimizer.log -Wait
```

### Debug in VS Code

```json
// .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: MCP Server",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/src/mcp_server.py",
            "console": "integratedTerminal"
        }
    ]
}
```

## Performance Optimization

### Profiling

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Your code here

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)
```

### Caching Strategy

```python
# Use cache manager
from src.api.cache_manager import CacheManager

cache = CacheManager()
await cache.initialize()

# Set cache
await cache.set("key", data, ttl=3600)

# Get from cache
cached = await cache.get("key")
```

## Code Style

### Formatting

```bash
# Format with black
black src/ tests/

# Sort imports
isort src/ tests/

# Lint
flake8 src/ tests/

# Type checking
mypy src/
```

### Style Guidelines

- Use type hints
- Write docstrings
- Keep functions focused
- Use async/await
- Handle errors gracefully

## Common Tasks

### Add a New Optimizer

1. Create file in `src/optimizer/`
2. Implement optimization logic
3. Register in `src/mcp_server.py`
4. Add tests
5. Update documentation

### Add Data Seeding

```python
# scripts/seed_new_data.py

import asyncio
from src.database.manager import DatabaseManager
from src.database.models import NewModel

async def seed_data():
    db = DatabaseManager()
    await db.initialize()

    # Add data
    async with db.async_session() as session:
        item = NewModel(name="Example", data={})
        session.add(item)
        await session.commit()

    await db.close()

if __name__ == "__main__":
    asyncio.run(seed_data())
```

## Troubleshooting

### Common Issues

**Import Errors**
```bash
# Add src to Python path
export PYTHONPATH="${PYTHONPATH}:${PWD}/src"
```

**Database Locked**
```bash
# Close all connections
rm data/poe2_optimizer.db-journal
```

**Rate Limit Errors**
```bash
# Increase limits in config.yaml
api:
  poe_api_rate_limit: 20  # Increase from 10
```

## Contributing Guidelines

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Update documentation
6. Submit a pull request

## Resources

- [Python AsyncIO](https://docs.python.org/3/library/asyncio.html)
- [SQLAlchemy](https://docs.sqlalchemy.org/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [MCP Protocol](https://modelcontextprotocol.io/)
- [PoE2 API Docs](https://www.pathofexile.com/developer/docs)

## Getting Help

- Check the [README.md](README.md) for usage instructions
- Review [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- See [QUICKSTART.md](QUICKSTART.md) for quick setup

## Next Steps

1. Set up your development environment
2. Run the test suite
3. Make a small change
4. Test your change
5. Contribute!

Happy coding!
