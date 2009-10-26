#!/bin/bash

VERSION=${1:-current}
REL_DIR="$(dirname $0)"

tar -C ${REL_DIR} --exclude .svn -cvzf ${REL_DIR}/tracktime-${VERSION}.tgz tt.py backup.sh html completion.bash static tasks | pr -tr -2
