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
echo ":${PATH}:" | grep -q ":${dirilivein}:"
if [ $? -ne 0 ]; then
    PATH="${PATH}:${dirilivein}"
fi

ttcomplete() { 
    #echo "1: \"$1\" 2: \"$2\" 3: \"$3\""
    # 2=current_typing_arg 3=previous_arg
    if [ "$1" == "$3" ]; then
	# nothing typed yet
	potentials=$(/bin/ls -ld ${TASKSDIR}/${2}* 2>&- | awk -F/ '/^d/{ print $NF }' | xargs)
	#printf " %s" $potentials
	COMPREPLY=(${potentials})
    elif [ "$3" == "-d" ]; then
	#potentials=$(sed -n 's/^ *formats *= *(\([^)]*\)) *$/\1/p' ${dirilivein}/tt.py | sed 's/, / /g')
	#COMPREPLY=(${potentials})
	COMPREPLY=('%Y-%m-%d %H:%M:%S' '%Y-%m-%d' '%Y-%m-%d %H:%M' '%m/%d' '%m/%d/%y' '%m/%d/%Y' '%m-%d-%y' '%m-%d-%Y' '%H:%M' '%M:%M:%S')
    elif [ -d "${TASKSDIR}/$3" ]; then
	#echo "1: \"$1\" 2: \"$2\" 3: \"$3\""
	# we are on minutes arg
	COMPREPLY=(30 60 90 120)
    else
        # okay, nothing special...
        #potentials=$(/bin/ls -d ${2}* 2>&- | xargs)
        eval files=$(/bin/echo ${2}* 2>&-)
        #potentials=$(for f in ${2}*; do if [ -d $f ]; then echo $f/; else echo $f; fi; done)
	potentials=$(for f in ${files}; do if [ -d $f ]; then echo $f/; else echo $f; fi; done)
        COMPREPLY=(${potentials})
    fi
}

complete -F ttcomplete tt.py
