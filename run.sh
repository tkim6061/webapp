#!/usr/bin/env bash

exec app/bin/server &
exec xdg-open app/build/index.html