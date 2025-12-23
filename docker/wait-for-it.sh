#!/bin/bash
# wait-for-it.sh: Wait for service availability before starting application
# Usage: ./wait-for-it.sh host:port -- command args

set -e

host="$1"
shift
cmd="$@"

until nc -z $host; do
  >&2 echo "Service $host is unavailable - sleeping"
  sleep 1
done

>&2 echo "Service $host is up - executing command"
exec $cmd
