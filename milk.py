#!/usr/bin/env python

import rtm, sys, os, time, re
REL_DIR = os.path.dirname(sys.argv[0])
if not REL_DIR: REL_DIR = '.'

# globals... you love 'em.
milk_key = ''
milk_sec = ''
milk_toc = ''

def create_milkinfo():
    """Ask some questions and create a ".milk.info" file with the needed API key, secret and eventually the token.
    """
    milk_key = raw_input("What is your Remember The Milk (RTM) api key? ")
    milk_sec = raw_input("And what is your RTM secret? ")
    print "Okay, we're going to generate a token based on your key and secret"
    mh = rtm.createRTM(milk_key, milk_sec)
    milk_toc = mh.authInfo.data['token']

    # We can actually do some more initialization now
    lists = mh.lists.getList()
    ll = [ l for l in lists.lists.list if l.name == 'TrackTime' ]
    if ll:
        tt_list = ll[0]
    else:
        timeline = mh.timelines.create()
        tt_list = mh.lists.add(timeline=timeline.timeline, name='TrackTime')
    milk_lid = tt_list.id

    try:
        fh = open('%s%s.milk.info' % (REL_DIR, os.sep), 'w')
        fh.write('milk_key=%s\nmilk_sec=%s\nmilk_toc=%s\nmilk_lid=%s\n' % (milk_key, milk_sec, milk_toc, milk_lid))
        fh.close()
    except (Exception), e:
        print 'Error: Could not writeout the .milk.info file: %s' % (str(e))

def init():
    """Read in the required information from the ".milk.info" file.
    Returns the API key, secret and token. All three used for a complete pyrtm initialization.
    """
    try:
        fh = open('%s%s.milk.info' % (REL_DIR, os.sep), 'r')
        milk_info = fh.read()
        fh.close()
        milk_key = re.findall('^milk_key=(.*)$', milk_info, re.M)[0]
        milk_sec = re.findall('^milk_sec=(.*)$', milk_info, re.M)[0]
        milk_toc = re.findall('^milk_toc=(.*)$', milk_info, re.M)[0]
        milk_lid = re.findall('^milk_lid=(.*)$', milk_info, re.M)[0]
        return milk_key, milk_sec, milk_toc, milk_lid
    except (Exception), e:
        return '', '', '', ''

def printtodos(mh, list_id):
    """ Prints out the tasks in the particular list
    """
    # Now list out the tasks in that list
    tasks = mh.tasks.getList(list_id=list_id)
    print 'TrackTime RTM tasks:'
    for task in tasks.tasks.list.taskseries:

        if task.task.completed:
            line = '--"%s"--' % (task.name)
        else:
            line = '  "%s"' % (task.name)
        if task.task.due:
            line += ' due on %s' % (task.task.due)
        else:
            line += ' no duedate' 
        if task.tags:
            line += ' #%s' % (task.tags.tag)
        print line
        if task.notes:
            for i, note in enumerate(task.notes.note):
                print '    Note(%d): %s' % (i, getattr(note, '$t'))

if __name__ == "__main__":

    # Get necessary auth information for RTM... or first time generate it.
    milk_key, milk_sec, milk_toc, milk_lid = init()
    if not milk_key:
        create_milkinfo()
    milk_key, milk_sec, milk_toc, milk_lid = init()

    # Create a milk handle (mh) for the RTM operations
    mh = rtm.createRTM(milk_key, milk_sec, token=milk_toc)

    # Add - [epoch, task, minutes, title]
    USAGE = """Usage: milk.py add|update|complete|uncomplete project duedate minutes title
       milk.py list"""
    try:
        if sys.argv[1] == "list":
            printtodos(mh, milk_lid)
            sys.exit(0)
        action, project, duedate, minutes, title = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], ' '.join(sys.argv[5:])
        #print 'DEBUG: "%s" to project "%s" identified by title "%s" for %s min' % (action, project, title, minutes)
    except (ValueError, IndexError), e:
        print USAGE
        sys.exit(1)

    # Need a timeline argument for a handful of calls.
    tl = mh.timelines.create()

    if action == "add":
        newtask = mh.tasks.add(timeline=tl.timeline, list_id=milk_lid, name="%s ^%s =%s min #%s" % (title, duedate, minutes, project), parse="1")

    elif action == "complete":
        tasks = mh.tasks.getList(list_id=milk_lid)
        found_ts = [ ts for ts in tasks.tasks.list.taskseries if ts.name == title ]
        if found_ts:
            ts = found_ts[0]
            mh.tasks.complete(timeline=tl.timeline, list_id=milk_lid, taskseries_id=ts.id, task_id=ts.task.id)

    elif action == "uncomplete":
        tasks = mh.tasks.getList(list_id=milk_lid)
        found_ts = [ ts for ts in tasks.tasks.list.taskseries if ts.name == title ]
        if found_ts:
            ts = found_ts[0]
            mh.tasks.uncomplete(timeline=tl.timeline, list_id=milk_lid, taskseries_id=ts.id, task_id=ts.task.id)

    sys.exit(0)
    #-POC------------------------------------------------------------------
    
    # milk handle
    mh = rtm.createRTM(milk_key, milk_sec, token=milk_toc)

    # Need a timeline argument for a handful of calls.
    timeline = mh.timelines.create()

    # List out the lists
    lists = mh.lists.getList()
    list_names = [ l.name for l in lists.lists.list ]
    print "You have the following lists on RTM:\n  %s" % (', '.join(list_names))

    # Add the TrackTime list if not present
    if 'TrackTime' not in list_names:
        print 'Creating the "TrackTime" list for you.'
        mh.lists.add(timeline=timeline.timeline, name='TrackTime')

    fav_list = 'Personal'
    # Now list out the tasks in that list
    ml = [ l for l in lists.lists.list if l.name == fav_list ][0]
    tasks = mh.tasks.getList(list_id=ml.id)

    print '\nPer the "%s" list:' % (fav_list)
    for task in tasks.tasks.list.taskseries:
        print '  %s: "%s" - updated on %s' % (task.id, task.name, task.modified)
        if task.notes:
            for i, note in enumerate(task.notes.note):
                print '    Note(%d): %s' % (i, getattr(note, '$t'))

    # Now let's create a new task
    dt_str = time.strftime('%j-%H:%M', time.localtime())
    newtask = mh.tasks.add(timeline=timeline.timeline, list_id=ml.id, name="Test task added from pyRTM #TrackTime", parse="1")
    # Now add a tag for that task
    #mh.tasks.setTags(timeline=timeline.timeline, list_id=task_add.list.id, taskseries_id=task_add.list.taskseries.id, task_id=, tags=dt_str)

    #sys.exit(0)
