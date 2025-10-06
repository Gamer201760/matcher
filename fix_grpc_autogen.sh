#!/bin/bash
# Скрипт для заменый путей на правильный в сгенерированных grpc контрактах
set -e

PROTO_PATH=$1
PREFIX=$2

if [ -z "$PROTO_PATH" ]; then
  echo "Usage: $0 <path> <package-prefix>";
  exit 1;
fi

if [ -z "$PREFIX" ]; then
  echo "Usage: $0 <path> <package-prefix>";
  exit 1;
fi

TARGET="$PROTO_PATH"

cd "$TARGET"

for dir in $(find . -type d); do
  pkgName="$( echo $dir | perl -pE 's/^\.\///g' | perl -pE 's/\//\./g' )"
  echo "$pkgName -> $PREFIX.$pkgName"
  pkgRegex="$( echo $pkgName | perl -pE 's/\./\\\./g' )"
  find $dir -mindepth 1 -maxdepth 1 -type f -name "*.py*" | xargs perl -pi -E "s/^from ($pkgName)/from $PREFIX.\$1/g"
  find $dir -maxdepth 1 -maxdepth 1 -type f -name "*.py*" | xargs perl -pi -E "s/^import ($pkgName)/import $PREFIX.\$1/g"
  find $dir -maxdepth 1 -maxdepth 1 -type f -name "*.pyi" | xargs perl -pi -E "s/\[($pkgName)\./\[$PREFIX.\$1\./g"
done
