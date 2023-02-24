#!/usr/bin/env bash

exec app/bin/server &
exec google-chrome app/build/index.html