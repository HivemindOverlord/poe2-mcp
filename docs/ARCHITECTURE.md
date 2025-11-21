# PoE2 Build Optimizer - System Architecture

## Overview

This document describes the complete architecture of the Path of Exile 2 Build Optimizer MCP Server.

## System Components

### 1. MCP Server (`src/mcp_server.py`)

**Purpose**: Main server implementing the Model Context Protocol

**Key Features**:
- 10 MCP tools for build analysis and optimization
- Natural language query interface
- Character data fetching from PoE API
- Build comparison and recommendations
- Path of Building import/export

**Tools Provided**:
1. `analyze_character` - Comprehensive character analysis
2. `natural_language_query` - AI-powered Q&A
3. `optimize_gear` - Gear upgrade recommendations
4. `optimize_passive_tree` - Passive tree optimization
5. `optimize_skills` - Skill setup optimization
6. `compare_builds` - Build comparison
7. `import_pob` - Import Path of Building codes
8. `export_pob` - Export to PoB format
9. `search_items` - Search game database
10. `calculate_dps` - Detailed DPS calculations

### 2. API Integration Layer (`src/api/`)

**Components**:

**poe_api.py** - Official PoE API Client
- OAuth 2.0 support (ready for implementation)
- Character data retrieval
- Account information fetching
- Passive tree and item data

**rate_limiter.py** - Adaptive Rate Limiting
- Token bucket algorithm
- Adaptive backoff on failures
- Per-endpoint rate limiting
- Statistics tracking

**cache_manager.py** - Multi-Tier Caching
- L1: In-memory cache (fastest, 1000 items)
- L2: Redis cache (optional, shared)
- L3: SQLite cache (persistent)
- Automatic expiry management

### 3. Database Layer (`src/database/`)

**models.py** - SQLAlchemy Models
- `Item` - Base item types
- `UniqueItem` - Unique items
- `Modifier` - Item/passive modifiers
- `PassiveNode` - Passive tree nodes
- `PassiveConnection` - Tree node connections
- `SkillGem` - Active skill gems
- `SupportGem` - Support gems
- `Ascendancy` - Ascendancy classes
- `SavedBuild` - User-saved builds
- `GameDataVersion` - Data versioning

**manager.py** - Database Manager
- Async database operations
- Item search
- Passive tree queries
- Build persistence
- Connection management

### 4. Calculator Engine (`src/calculator/`)

**build_scorer.py** - Build Quality Scoring
- 0.0-1.0 overall quality score
- Tier ranking (S/A/B/C/D)
- Strength/weakness identification
- Gear, passive, and skill scoring
- Build comparison

### 5. Optimizer Modules (`src/optimizer/`)

**gear_optimizer.py** - Gear Recommendations
- Slot-by-slot analysis
- Budget-aware suggestions
- Priority ranking
- Goal-specific optimization

**passive_optimizer.py** - Passive Tree
- Point allocation recommendations
- Respec suggestions
- Efficient pathing
- Keystone analysis

**skill_optimizer.py** - Skill Setup
- Gem combination suggestions
- Link priority
- Support gem recommendations

### 6. AI Components (`src/ai/`)

**query_handler.py** - Natural Language Processing
- Claude AI integration
- Context-aware responses
- Build-specific answers

**recommendation_engine.py** - AI Recommendations
- Comprehensive build analysis
- Actionable suggestions
- Personalized advice

### 7. Path of Building Integration (`src/pob/`)

**importer.py** - PoB Import
- Base64 decoding
- XML parsing
- Build data extraction

**exporter.py** - PoB Export
- Build XML generation
- Compression and encoding
- PoB-compatible format

## Data Flow

```
User Query (via Claude Desktop)
    ↓
MCP Server receives tool call
    ↓
Rate Limiter checks quota
    ↓
Cache Manager checks for cached data
    ↓ (if cache miss)
PoE API Client fetches data
    ↓
Database Manager stores/retrieves game data
    ↓
Calculator/Optimizer processes data
    ↓
AI Components generate insights (if enabled)
    ↓
Response formatted and returned
    ↓
Cache Manager stores result
    ↓
User receives formatted analysis
```

## Caching Strategy

### L1: Memory Cache
- **Duration**: 5 minutes
- **Size**: 1000 items max
- **Use**: Frequently accessed data
- **Speed**: Instant

### L2: Redis Cache (Optional)
- **Duration**: 1 hour
- **Size**: Unlimited
- **Use**: Shared across instances
- **Speed**: < 1ms

### L3: SQLite Cache
- **Duration**: Persistent
- **Size**: Unlimited (auto-cleanup)
- **Use**: Long-term storage
- **Speed**: < 10ms

## Rate Limiting

### Strategy
- Token bucket algorithm
- Adaptive backoff (2^n)
- Per-endpoint limits
- Failure tracking

### Default Limits
- PoE Official API: 10 req/min
- poe2db.tw: 30 req/min
- poe.ninja: 20 req/min

### Adaptive Behavior
- Success: Reset backoff
- Failure: 2x backoff (max 32x)
- Consecutive failures: Exponential increase

## Database Schema

### Core Tables
- **items**: ~10,000 items
- **unique_items**: ~500 uniques
- **modifiers**: ~5,000 modifiers
- **passive_nodes**: ~1,500 nodes
- **skill_gems**: ~200 skills
- **support_gems**: ~150 supports

### User Tables
- **saved_builds**: User builds
- **optimization_history**: Past results

## Performance Targets

- **Character Analysis**: < 500ms
- **Gear Optimization**: < 1s
- **Passive Optimization**: < 2s
- **Full Build Analysis**: < 3s
- **Natural Language Query**: < 5s (AI dependent)

## Scalability

### Vertical Scaling
- Increase worker count
- Larger cache size
- Better hardware

### Horizontal Scaling
- Redis cache sharing
- Load balancer
- Multiple server instances

## Security

### API Security
- Rate limiting per user
- Request validation
- SQL injection prevention
- XSS protection

### Data Privacy
- No credential storage
- Local-first approach
- Optional cloud sync (encrypted)
- User data isolation

## Monitoring

### Metrics Tracked
- API call counts
- Cache hit rates
- Response times
- Error rates
- Rate limit usage

### Logging
- Request/response logging
- Error tracking
- Performance profiling
- User activity (anonymous)

## Extensibility

### Adding New Tools
1. Define tool in `_register_tools()`
2. Implement handler method
3. Add supporting modules
4. Update documentation

### Adding Data Sources
1. Create new API client
2. Add rate limiter
3. Implement caching
4. Map to database models

### Adding Optimizers
1. Create optimizer class
2. Implement optimization logic
3. Register in MCP server
4. Add tests

## Technology Stack

### Core
- Python 3.9+
- FastAPI (future web API)
- SQLAlchemy (ORM)
- MCP Protocol

### APIs
- httpx (async HTTP)
- aiohttp (async requests)

### AI
- Anthropic Claude API
- OpenAI (alternative)

### Caching
- aioredis (Redis)
- aiosqlite (SQLite)

### Data Processing
- pandas (optional)
- numpy (optional)

## Development Workflow

### Setup
```bash
python setup.py
```

### Run
```bash
python launch.py
```

### Test
```bash
pytest tests/
```

### Deploy
```bash
# Add to Claude Desktop config
# Or run as standalone server
```

## Future Enhancements

### Phase 1 (Current)
- [x] MCP server foundation
- [x] API integration
- [x] Database models
- [x] Basic caching
- [x] Rate limiting

### Phase 2
- [ ] Complete calculator engine
- [ ] Full optimizer implementations
- [ ] Comprehensive game data seeding
- [ ] Web interface

### Phase 3
- [ ] Trade integration
- [ ] Build sharing
- [ ] Meta analysis
- [ ] Advanced AI features

### Phase 4
- [ ] Mobile app
- [ ] Real-time notifications
- [ ] Community features
- [ ] Tournament support

## Contributing

This is a personal project, but well-structured for extensions:
- Clear module separation
- Comprehensive documentation
- Type hints throughout
- Async-first design

## References

- [MCP Protocol](https://modelcontextprotocol.io/)
- [PoE2 API Documentation](https://www.pathofexile.com/developer/docs)
- [poe2db.tw](https://poe2db.tw) - Game data source
- [Path of Building](https://github.com/PathOfBuildingCommunity/PathOfBuilding)
