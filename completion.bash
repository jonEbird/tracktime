#!/bin/bash

# This is intended to be sourced
# 
# Add a line to your .bash_profile which looks like: (obviously fix the pathing)
#   source /path/to/this/directory/completion.bash /path/to/this/directory/
# Or these lines if you have decided to use an alternate tasks directory
#   source /path/to/this/directory/completion.bash /path/to/this/directory/ /alternate/path/to/tasks/
#

cd $1; dirilivein=$(pwd); cd ~-
TASKSDIR=${2:-${dirilivein}/tasks}
cd $TASKSDIR; TASKSDIR=$(pwd); cd ~- # want absolute pathing, but calling this can use relative

# help you out if you choose an alternate directory
if [ "${dirilivein}/tasks" != "$TASKSDIR" ]; then
    alias tt.py="tt.py --taskdir=$TASKSDIR "
fi

# Let's update your PATH considering you'll be using this.
if ! echo ":${PATH}:" | grep -q ":${dirilivein}:"; then
    PATH="${PATH}:${dirilivein}"
fi

ttcomplete() { 
    #echo "1: \"$1\" 2: \"$2\" 3: \"$3\""
    # 2=current_typing_arg 3=previous_arg
    COMPREPLY=()
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local prev="${COMP_WORDS[COMP_CWORD-1]}"

    if [ "${prev}" == "-d" ]; then
	#echo "Case #1"
	COMPREPLY=('%Y-%m-%d %H:%M:%S' '%Y-%m-%d' '%Y-%m-%d %H:%M' '%m/%d' '%m/%d/%y' '%m/%d/%Y' '%m-%d-%y' '%m-%d-%Y' '%H:%M' '%M:%M:%S')
    elif [ -d "${TASKSDIR}/$3" ]; then
	#echo "Case #2"	# we are on minutes arg
	COMPREPLY=(30 60 90 120)
    else
	#echo "Case #3"
	#COMPREPLY=( $(compgen -f "${TASKSDIR}/${cur}") )
	COMPREPLY=( $(compgen -f $TASKSDIR/${cur} | sed "s|^${TASKSDIR}/||g") )
    fi
}

complete -F ttcomplete tt.py
