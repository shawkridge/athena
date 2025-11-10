# Phase 3: Quick Start Guide

## Current State
- **Tests**: 207/207 passing ✅
- **Status**: 98% complete, production-ready
- **Gaps**: 4 items (2% remaining)

## Before You Start

1. **Read the full context**:
   ```bash
   cat PHASE_3_CONTEXT.md
   ```

2. **Check current test status**:
   ```bash
   pytest tests/ -q --tb=no
   # Should see: 207 passed
   ```

3. **Understand what's left**:
   - Priority 1: MCP handler integration tests (1-2 days)
   - Priority 2: Monitoring integration (2-3 days)
   - Priority 3: Security review (1-2 days)
   - Priority 4: Deployment automation (2-3 days)

## How to Pick Your Next Task

### If you want to increase test coverage:
```bash
# Start with Priority 1: MCP Handler Tests
cd /home/user/.work/athena

# Create the test file
touch tests/mcp/test_handlers_integration.py

# Use template from PHASE_3_CONTEXT.md, section "Priority 1"
# Goal: 30-40 integration tests, >80% handler coverage

pytest tests/mcp/test_handlers_integration.py -v
```

### If you want to improve observability:
```bash
# Start with Priority 2: Monitoring Integration
cd /home/user/.work/athena

# Create monitoring modules
mkdir -p src/athena/monitoring
touch src/athena/monitoring/{exporters.py,structured_logging.py}

# Use templates from PHASE_3_CONTEXT.md, section "Priority 2"
# Goal: Prometheus exporter, JSON logging, alerting rules

# Test the exporter
curl http://localhost:8000/metrics
```

### If you want to improve security:
```bash
# Start with Priority 3: Security Review
cd /home/user/.work/athena

# Add validation and rate limiting
# Follow examples in PHASE_3_CONTEXT.md, section "Priority 3"

# Run security checks
bandit -r src/athena
detect-secrets scan src/
```

### If you want to enable production deployment:
```bash
# Start with Priority 4: Deployment Automation
cd /home/user/.work/athena

# Create Docker setup
mkdir -p docker scripts
touch docker/{Dockerfile,docker-compose.yml}
touch scripts/{deploy.sh,healthcheck.sh}

# Use templates from PHASE_3_CONTEXT.md, section "Priority 4"
# Goal: Dockerized deployment with health checks

docker-compose up -d
docker-compose ps
```

## Standard Session Flow

### Each session should follow this pattern:

```
1. SETUP (5 minutes)
   ✓ Read PHASE_3_CONTEXT.md section for your priority area
   ✓ Review existing tests for code patterns
   ✓ Run: pytest tests/ -q (verify baseline passing)

2. IMPLEMENT (30-90 minutes)
   ✓ Create test file(s) or source files
   ✓ Use templates from PHASE_3_CONTEXT.md
   ✓ Follow existing code patterns
   ✓ Add docstrings and comments

3. VALIDATE (10-30 minutes)
   ✓ Run: pytest <your_new_tests> -v
   ✓ Run: pytest tests/ -q (verify no regressions)
   ✓ Check coverage: pytest --cov=src/athena

4. COMMIT (5 minutes)
   ✓ git add <files>
   ✓ git commit -m "feat/docs: Description"
   ✓ git log --oneline -1 (verify)
```

## File Structure Reference

### Where to create new files:

**For MCP Handler Tests**:
```
tests/mcp/test_handlers_integration.py    ← Create here
Reference: src/athena/mcp/handlers.py
```

**For Monitoring**:
```
src/athena/monitoring/exporters.py
src/athena/monitoring/structured_logging.py
tests/monitoring/test_exporters.py        ← Test here
```

**For Security**:
```
src/athena/security/validators.py
src/athena/security/rate_limiter.py
tests/security/test_validators.py         ← Test here
docs/SECURITY_AUDIT.md                    ← Documentation
```

**For Deployment**:
```
docker/Dockerfile
docker/docker-compose.yml
scripts/deploy.sh
scripts/healthcheck.sh
docs/DEPLOYMENT.md                        ← Documentation
```

## Common Commands

### Testing
```bash
# Run all tests
pytest tests/ -v

# Run specific priority area
pytest tests/mcp/test_handlers_integration.py -v
pytest tests/monitoring/ -v
pytest tests/security/ -v

# Check coverage
pytest --cov=src/athena --cov-report=html

# Run with output
pytest tests/mcp/test_handlers_integration.py -v -s
```

### Code Quality
```bash
# Format code
black src/ tests/

# Lint code
ruff check --fix src/ tests/

# Type check
mypy src/athena

# Security check
bandit -r src/athena
```

### Git Workflow
```bash
# Check status
git status

# Stage files
git add <files>

# Commit with message
git commit -m "feat: Add MCP handler integration tests"

# View recent commits
git log --oneline -5
```

## Success Checklist for Each Priority

### Priority 1: MCP Handler Tests ✓
- [ ] File created: `tests/mcp/test_handlers_integration.py`
- [ ] Tests written: 30-40 tests covering all 27 MCP tools
- [ ] Coverage: >80% for `src/athena/mcp/handlers.py`
- [ ] All tests passing: `pytest tests/mcp/test_handlers_integration.py -v`
- [ ] No regressions: `pytest tests/ -q` shows same count passing
- [ ] Committed: `git log` shows your commit

### Priority 2: Monitoring Integration ✓
- [ ] File created: `src/athena/monitoring/exporters.py`
- [ ] File created: `src/athena/monitoring/structured_logging.py`
- [ ] File created: `monitoring/prometheus.yml` (config)
- [ ] File created: `monitoring/alert_rules.yaml`
- [ ] File created: `docs/MONITORING.md`
- [ ] Tests written: `tests/monitoring/test_exporters.py`
- [ ] Metrics exposed: Verify `/metrics` endpoint works
- [ ] JSON logs: Verify logs are valid JSON
- [ ] Committed: New files tracked in git

### Priority 3: Security Review ✓
- [ ] File created: `src/athena/security/validators.py`
- [ ] File created: `src/athena/security/rate_limiter.py`
- [ ] File created: `docs/SECURITY_AUDIT.md`
- [ ] Validation added to MCP tools
- [ ] Rate limiting implemented
- [ ] Audit logging added
- [ ] Tests passing: `pytest tests/security/ -v`
- [ ] Security checks passing: `bandit -r src/athena`
- [ ] Committed: Changes tracked in git

### Priority 4: Deployment Automation ✓
- [ ] File created: `docker/Dockerfile`
- [ ] File created: `docker/docker-compose.yml`
- [ ] File created: `scripts/deploy.sh`
- [ ] File created: `scripts/healthcheck.sh`
- [ ] File created: `docs/DEPLOYMENT.md`
- [ ] Docker image builds: `docker-compose build` succeeds
- [ ] Services start: `docker-compose up -d` works
- [ ] Health checks pass: `docker-compose ps` shows healthy
- [ ] Tests run in container: `docker-compose exec athena pytest tests/ -v`
- [ ] Committed: All files tracked in git

## Template Prompts for Starting New Work

### For MCP Handler Tests:
```
I'm implementing Priority 1 of Phase 3: MCP Handler Integration Tests.

Current status: 207/207 tests passing
Goal: Add 30-40 integration tests for MCP handlers

Reference: PHASE_3_CONTEXT.md section "Priority 1"

Please:
1. Create tests/mcp/test_handlers_integration.py
2. Write integration tests covering all 27 MCP tools
3. Ensure >80% coverage for src/athena/mcp/handlers.py
4. Make sure all tests pass and no regressions

Let me know when complete!
```

### For Monitoring Integration:
```
I'm implementing Priority 2 of Phase 3: Production Monitoring Integration.

Current status: 207/207 tests passing
Goal: Add Prometheus exporter and structured logging

Reference: PHASE_3_CONTEXT.md section "Priority 2"

Please:
1. Create Prometheus exporter (src/athena/monitoring/exporters.py)
2. Implement structured logging (src/athena/monitoring/structured_logging.py)
3. Create alerting rules and monitoring guide
4. Write tests to verify metrics and logs are working

Let me know when complete!
```

### For Security Review:
```
I'm implementing Priority 3 of Phase 3: Security Review.

Current status: 207/207 tests passing
Goal: Add input validation, rate limiting, and audit logging

Reference: PHASE_3_CONTEXT.md section "Priority 3"

Please:
1. Add input validation to MCP tools
2. Implement rate limiting per operation
3. Add audit logging for sensitive operations
4. Create SECURITY_AUDIT.md documentation

Let me know when complete!
```

### For Deployment:
```
I'm implementing Priority 4 of Phase 3: Deployment Automation.

Current status: 207/207 tests passing
Goal: Create Docker setup and deployment automation

Reference: PHASE_3_CONTEXT.md section "Priority 4"

Please:
1. Create Docker setup (Dockerfile, docker-compose.yml)
2. Write deployment scripts (deploy.sh, healthcheck.sh)
3. Create deployment documentation
4. Verify all services start and health checks pass

Let me know when complete!
```

## Estimated Timeline

- **Priority 1 (MCP Tests)**: 1-2 days → +40 tests
- **Priority 2 (Monitoring)**: 2-3 days → Production observability
- **Priority 3 (Security)**: 1-2 days → Security hardening
- **Priority 4 (Deployment)**: 2-3 days → Docker + automation
- **Priority 5 (Staging)**: 3-5 days → Validation and sign-off

**Total**: 2-3 weeks to close all gaps and deploy to production

## Quick Reference Commands

```bash
# Run everything that needs to pass
pytest tests/ -q && black src/ tests/ && ruff check src/ tests/ && mypy src/athena

# Just see what changed
git status

# See what you're about to commit
git diff --cached

# Quick test of specific area
pytest tests/mcp/ -v -k "recall"

# Check if Docker works
docker-compose up -d && docker-compose ps && docker-compose down

# View latest commits
git log --oneline -10
```

## Getting Help

If stuck:
1. Check `PHASE_3_CONTEXT.md` for detailed examples
2. Review existing tests in `tests/unit/` for patterns
3. Look at `DEVELOPMENT_GUIDE.md` for workflows
4. Run: `git log --oneline` to see previous patterns

## Next Step

Pick your priority area and use the corresponding template prompt!

---

**Last Updated**: November 10, 2025
**Phase**: Phase 3 - Production Hardening
**Status**: Ready to start
