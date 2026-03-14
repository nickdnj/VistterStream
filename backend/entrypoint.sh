#!/bin/bash
# Fix ownership of /data volume (may have been created by root in previous deploys)
# then drop to appuser and run the application
if [ "$(id -u)" = "0" ]; then
    chown -R appuser:appuser /data
    exec gosu appuser "$@"
else
    exec "$@"
fi
