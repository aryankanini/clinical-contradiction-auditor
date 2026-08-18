# PlantUML Diagram Rendering Status

## Diagrams Created
The following PlantUML diagrams have been generated as `.puml` source files:

| Diagram | File | Status | Notes |
|---------|------|--------|-------|
| UC-1: Submit FHIR Batch | `uc-001-submit-batch.puml` | Created | Use case for batch ingestion workflow |
| UC-2: Detect Contradictions | `uc-002-detect-contradictions.puml` | Created | Use case for rule evaluation and finding generation |
| UC-3: AI-Driven Explanation | `uc-003-ai-explanation.puml` | Created | Use case for LLM-based finding explanation |
| UC-4: Assignment & Tracking | `uc-004-assignment-tracking.puml` | Created | Use case for finding triage and resolution workflow |
| UC-5: Audit Reproducibility | `uc-005-audit-reproducibility.puml` | Created | Use case for compliance audit trail verification |

## Rendering Status
- **Online Rendering**: Failed (403 Forbidden - service access restricted)
- **Local Rendering**: Requires PlantUML installation or Python library

## To Render Diagrams Locally

### Option 1: Using PlantUML CLI (Recommended)
```bash
# Install PlantUML (requires Java)
# Download from: https://plantuml.com/download

# Render all diagrams
plantuml .propel/uml/*.puml -png

# Render single diagram
plantuml .propel/uml/uc-001-submit-batch.puml -png
```

### Option 2: Using Python + PlantUML Library
```bash
pip install plantuml
python -m plantuml .propel/uml/*.puml
```

### Option 3: Using Docker
```bash
docker run --rm -v $(pwd)/.propel/uml:/data think/plantuml:latest *.puml -png
```

## Next Steps
Diagrams are ready for rendering when PlantUML is available in the environment. The `.puml` source files can be:
1. Committed to version control as code-based documentation
2. Rendered on-demand for presentations and documentation
3. Integrated into CI/CD pipeline for automated rendering on each commit

All diagrams follow standard UML use case notation and are compatible with PlantUML, Visual Paradigm, Lucidchart, and other tools supporting PlantUML syntax.
