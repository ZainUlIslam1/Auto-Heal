# Healenium Starter (IPR-friendly)

## Prereqs
- Java 11+ and Maven
- Chrome + matching ChromeDriver on PATH
- Docker & Docker Compose

## Start Healenium stack
```
docker compose up -d
# Reporter: http://localhost:8080
```

## Run demo
```
# 1) Learn (stores baseline)
mvn -q -Dexec.args=learn exec:java

# 2) Heal (uses wrong locator; Healenium should heal)
mvn -q -Dexec.args=heal exec:java
```

## Analyse in R
```
Rscript analysis/healing_metrics.R
```
Check `runs/` for log files and include plots/tables in your IPR.
