#!/bin/bash

REL_DIR=$(dirname $0)
WEEK=$(($(date +%j | sed 's/^0*//g') / 7))

[ ! -d ${REL_DIR}/.backup ] && mkdir ${REL_DIR}/.backup

# gets me the TASKSDIR location and sets up an alias fix for tt.py when necessary
source ${REL_DIR}/completion.bash ${REL_DIR}

# backup normal logged events
${REL_DIR}/tt.py -lab > ${REL_DIR}/.backup/tt_backup.week${WEEK}

if [ -d $TASKSDIR ]; then
    for subdir in ${TASKSDIR}/*; do
	if [ -d $subdir ]; then
	    task="$(basename $subdir)"
	    ${REL_DIR}/tt.py "$task" -lfb > "${REL_DIR}/.backup/tt_backupfuture_${task}.week${WEEK}"
	    [ ! -s "${REL_DIR}/.backup/tt_backupfuture_${task}.week${WEEK}" ] && rm "${REL_DIR}/.backup/tt_backupfuture_${task}.week${WEEK}"
	fi
    done
else
    echo "Error: Can not backup future tasks. Please fix your ${REL_DIR}/completion.bash file so that it properly sets \$TASKSDIR" 1>&2
    echo "       Alternatively, manually set the \$TASKSDIR here in this script: $0" 1>&2
fi
