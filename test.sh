#!/bin/sh
cd $(dirname "$0")
./make install && gnsu -E bootsetup --test "$@"
