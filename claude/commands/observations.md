---
description: Add context and observations to knowledge graph entities
allowed-tools: mcp__memory__add_observation, mcp__memory__search_graph
group: memory-management
---

# /observations - Entity Context Management

## Overview

Enrich knowledge graph entities with observations and context. Add notes to entities discovered during research, making your knowledge graph more contextual and interconnected.

## Usage

```
/observations <entity_id> [--add "observation"] [--list] [--remove <obs_id>]
```

## Commands

### List Entity Observations
```
/observations 42
```

Shows all observations for entity #42.

### Add Observation
```
/observations 42 --add "This relates to temporal chains"
```

Add context note to entity.

### Remove Observation
```
/observations 42 --remove 12
```

Delete specific observation.

## Examples

```
/observations 156 --add "Key bridge entity - connects memory and learning"
/observations 201 --add "Implemented in working_memory/models.py"
/observations 312 --add "Performance bottleneck - needs optimization"
```

## Integration

Observations make your graph more useful:
- Provide human context to automated entities
- Record discovery notes
- Document key insights
- Mark important connections

## Related Commands

- `/associations` - View entity connections
- `/memory-query` - Search including observations
- `/memory-health` - Entity context affects health

## See Also

- **Knowledge Graph:** Semantic networks
- **Entity Annotations:** Metadata enrichment
- **Context:** Background knowledge importance
