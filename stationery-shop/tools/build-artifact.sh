#!/bin/sh
# Produces dist/index.html without the document wrapper (for hosts that supply their own <html>/<head>/<body>).
set -e
cd "$(dirname "$0")/.."
mkdir -p dist
grep -v -i -E '^\s*(<!doctype html>|<html[^>]*>|</html>|<head>|</head>|<body>|</body>)\s*$' index.html > dist/index.html
