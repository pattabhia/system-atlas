#!/usr/bin/env bash
# Build the Stage B symbol-solving call-graph jar. Free/OSS only (JavaParser, Apache-2.0).
# Produces target/callgraph.jar. Requires mvn + a JDK 21 and (first build) network to Maven Central.
set -euo pipefail
cd "$(dirname "$0")"
mvn -q -DskipTests package
echo "built: $(pwd)/target/callgraph.jar"
