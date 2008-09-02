#!/usr/bin/env python

from sqlobject import *
import sys, os, glob, time, datetime, re, StringIO, hashlib, getpass
from math import log
from stat import *

import web
web.webapi.internalerror = web.debugerror
render = web.template.render('html/')
static = web.template.render('static/')

urls = (
      '/', 'IndexURL',
      '/login', 'LoginURL',
      '/logout', 'LogoutURL',
      '/static/(\w+)', 'StaticURL',
      '/tasks', 'TasksURL',
      '/journal/(\w+)', 'JournalURL',
      '/today', 'JournalURL',
      '/futureedit/(.*)', 'FutureeditURL',
      '/future/?(.*)', 'FutureURL',
      '/dayof/(\d+)/(\d+)/(\d+)', 'DayViewURL',
      '/testdayof/(\d+)/(\d+)/(\d+)', 'TestURL',
      '/newtaskon/(\d+)/(\d+)/(\d+)/(-?\d+)', 'NewTaskURL',
      '/weekof/(\d+)/(\d+)/(\d+)', 'WeekViewURL',
      '/bars/(\d+)/(\d+)/(\d+)/to/(\d+)/(\d+)/(\d+)', 'BargraphURL',
      '/deltask/(\d+)', 'deltaskURL',
      '/updatetask/(\w+)/(-?\d+)', 'UpdateURL',
      '/edittodobody/(\w+)/(\d+)', 'edittodolistURL',
      '/updatetodo/(\w+)/(\d+)', 'updatetodoURL',
      '/clockdatafor/(\w+)', 'clockdataURL'
  )

# Some GLOBAL variables
REL_DIR = os.path.dirname(sys.argv[0])
if not REL_DIR: REL_DIR = '.'
negative_tasks = 'lunch break' # whitespace separated tasks which take away from clocked in time
formats = ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y-%m-%d %H:%M', '%m/%d', '%m/%d/%y', '%m/%d/%Y', '%m-%d-%y', '%m-%d-%Y', '%H:%M', '%M:%M:%S')
long_future = 1999999999
transitiontime = 15 # time need to transition between one task to another (min)
weekstartson=0 # mon=0, tue=1, wed=2, thr=3, Fri=4, Sat=5, Sun=6
pixels_per_hour = 50
tasksdir = 'tasks'
unsure_task = 'unsure'
color_samples = [ '#b46224', '#d9b12d', '#76a4ab', '#030e34', '#292035', '#733510', '#fbb500', '#d47800', '#552712', '#ff8c00', '#bd3b00', '#760000', '#d61500', '#ff6700', '#221400', '#75470b', '#c53200', '#d58c20', '#433f3b', '#906f56', '#ae9e69', '#cfceb9', '#748689', '#161a29', '#25222a', '#5c4334', '#c8ad57', '#a98551', '#e2a94e', '#976337', '#5e2d1a', '#ab5e34', '#cd9065', '#54493e' ]
pam = ''
pam_service = ''

class Tasks(SQLObject):
    
    task = StringCol()
    start = DateTimeCol()
    end = DateTimeCol(default=None)

class Todos(SQLObject):

    task = StringCol()
    title = StringCol()
    body = StringCol()
    submitdate = DateTimeCol()
    modifydate = DateTimeCol()
    duedate = DateTimeCol()
    duration = IntCol()
    createdfrom = StringCol() # Can be '/path/to/file' or 'web' or 'editor'
    journal = StringCol() # Journal.id values space/comma separated. I.e. [ int(x) for x in s1.replace(',', ' ').split()]
    completed = BoolCol(default=False)
    # hidden = BoolCol(default=False)	# Why again? instead use heuristics to determine to suppress display
    # dependson = StringCol()		# do not need; too much work required on user, instead use simple dates

class User(SQLObject):
    class sqlmeta:
        table = "user_table"
    username = StringCol()
    password = StringCol()

class Session(SQLObject):
    sessionid = StringCol()
    username = StringCol()
    sourceip = StringCol()

class LoginURL:
    def GET(self):
        print render.login(cache=False)
    def POST(self):
        input = web.input()
        sha1 = hashlib.sha1()
        try:
            if pam:
                if not pam.authenticate(input.username, input.password, pam_service):
                    raise main.SQLObjectNotFound
            else:
                user = User.selectBy(username=input.username, password=input.password).getOne()

            # At this point you have succeeded
            sha1.update(input.password)
            Session(sessionid=sha1.hexdigest(), username=input.username, sourceip=web.ctx.ip)
            web.setcookie('tt_session', sha1.hexdigest())
            web.redirect(web.ctx.environ['HTTP_REFERER'])
        except (main.SQLObjectNotFound), e:
            pass
        web.redirect(web.ctx.environ['HTTP_REFERER'])

class LogoutURL:
    def GET(self):
        session = loggedin()
        if session:
            Session.delete(session.id)
            web.setcookie('tt_session', '')
        web.redirect(web.ctx.environ['HTTP_REFERER'])

class TestURL:
    def GET(self, year, month, day):
        tasks, clocks = getdaytasks(year, month, day)
        for j in tasks:
            print '%s(%d): %s\n' % (j.task, j.id, j.description)
        print '\nClocked Times:\n'
        for jt in clocks:
            print '%s\n' % (time.strftime('%c', jt))
        
class TasksURL:
    def GET(self):
        headerdata = getHeaderHTML()
        tasks = '<h3>Get some Tasks</h3>\n'
        for t in Tasks.select(orderBy=Tasks.q.task):
            tasks += '<p>\n   <form method="post" action="journal/%s">Task "%s": \n' % (t.task, t.task)
            tasks += '        <input style="{ width:200; }" type="text" name="journal">\n'
            tasks += '        <input styel="{ width:200; }" type="text" name="date">\n'
            tasks += '        <input style="{ width:20; }" type="text" name="minutes">\n'
            tasks += '        <input type="submit" value="log it">\n'
            tasks += '    </form>\n</p>\n'
        print render.tasks(headerdata, tasks, cache=False)

class NewTaskURL:
    def GET(self, year, month, day, delta):        

        options = ''
        for t in Tasks.select(orderBy=Tasks.q.task):
            options += '            <option value="%s">%s</option>\n' % (t.task, t.task)
        
        myform = """
<div id="newtask">
<form method="post" action="/newtaskon/%s/%s/%s/%s" class="newtask" name="taskinput">
<table cellspacing="0">
    <tr>
        <td class="lbl" >Task</td>
        <td class="inp">
          <select name="task" size="1">
%s
          </select>
        </td>        
        <td class="lbl" id="minutes">Minutes</td>
        <td class="inp"><input type="text" name="min" size="3"></td>
        <td class="lbl">Description</td>
        <td class="inp"><input type="text" name="desc" size="50"></td>
        <td class="submit"><input type="submit" value="submit"></td>
    </tr>
</table>
</form>
<form method="get" action="/dayof/%s/%s/%s" class="cancel">
    <input type="submit" value="cancel">
</form>
</div>
<div class="clear"></div>
""" % (year, month, day, delta, options, year, month, day)

        print myform

    def POST(self, year, month, day, delta):
        # Logged in or not?
        if not loggedin(): 
            web.redirect('/dayof/%s/%s/%s' % (year, month, day))
            return False

        __left = 50

        hour_begin = 7
        t1 = time.strptime('%s%s%s 12' % (year, month, day), '%Y%m%d %H')
        for j in Journal.select(AND(Journal.q.start >= datetime.datetime(int(year), int(month), int(day), 0,0,0), Journal.q.start <= datetime.datetime(int(year), int(month), int(day), 23,59,59)), orderBy=Journal.q.start):
            jt = time.strptime("%s" % j.start, '%Y-%m-%d %H:%M:%S')
            if jt.tm_hour < hour_begin:
                hour_begin = jt.tm_hour

        delta = int(delta) + 10 # the width of the placeable box
        delta_minutes = (delta - __left) * 60 / pixels_per_hour

        hour = hour_begin + (delta_minutes / 60)
        minutes = delta_minutes % 60

        t1 = time.strptime('%s%s%s %d:%d' % (year, month, day, hour, minutes), '%Y%m%d %H:%M')

        input = web.input()
        Journal(task=input.task, start=datetime.datetime(*t1[:6]), duration=int(input.min), description=input.desc)
        web.redirect('/dayof/%s/%s/%s' % (year, month, day))
        

class Journal(SQLObject):
    
    #task = ForeignKey('Tasks')
    task = StringCol()    
    start = DateTimeCol()
    description = StringCol()
    duration = IntCol() # minutes

def loggedin():
    session = ''
    try:
        mycookies = web.cookies()
    except AttributeError, e:
        # exception means you are not running the webserver
        # Allowing any command line access 
        return True
    try:
        s1 = Session.selectBy(sessionid=mycookies.tt_session, sourceip=web.ctx.ip)
    except (AttributeError, main.SQLObjectNotFound), e:
        return session

    try:
        i = iter(s1)
        for sess in i:
            if not session:
                session = sess
            else:
                # this is an extra login session which we'll cleanup now
                sess.delete(sess.id)
    except TypeError, e:
        session = s1.getOne()
    return session

def getHeaderHTML():
    now = time.localtime()
    y, m, d = time.strftime('%Y:%m:%d').split(':')
    headerdata = '<a href="/dayof/%s/%s/%s">today</a> | ' % (y, m, d)
    headerdata += '<a href="/weekof/%s/%s/%s">thisweek</a> | ' % (y, m, d)
    #headerdata += '<a href="/tasks">addjournal</a> | '
    lastday = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][int(m)-1]
    headerdata += '<a href="/bars/%s/%s/01/to/%s/%s/%d">thismonth</a> | ' % (y, m, y, m, lastday)
    headerdata += '<a href="/future">future</a>'

    # Logged in or not?
    session = loggedin()
    if session:
        headerdata += ' | hello %s - <a href="/logout">logout</a>' % session.username
    else:
        headerdata += render.login(cache=False)

    return headerdata

class IndexURL:
    def GET(self):
        headerdata = getHeaderHTML()
        print render.index(headerdata, cache=False)

class StaticURL:
    def GET(self, filename):
        print static.filename(cache=True)

class deltaskURL:
    def POST(self, id):
        input = web.input()
        j = Journal.get(id)
        t1 = time.strptime("%s" % j.start, '%Y-%m-%d %H:%M:%S')
        if not loggedin():
            web.redirect('/dayof/%04d/%02d/%02d' % (t1.tm_year, t1.tm_mon, t1.tm_mday))
            return False
        #print 'DELETING: (%d) %s: Worked on %s for %s minutes: %s' % (j.id, j.start, j.task, j.duration, j.description)
        j.delete(id)
        web.redirect('/dayof/%04d/%02d/%02d' % (t1.tm_year, t1.tm_mon, t1.tm_mday))

class JournalURL:
    def GET(self):
        for j in Journal.select(orderBy=Journal.q.start):
            print '%s: Worked on %s for %s minutes: %s' % (j.start, j.task, j.duration, j.description)

    def POST(self, task):
        input = web.input()
        if not loggedin():
            web.redirect('/tasks')
            return False
        print 'Okay, need to add a journal entry for "%s" with the TXT: %s' % (task, input.journal)
        Journal(task=task, start=DateTimeCol.now(), duration=int(input.minutes), description=input.journal)
        web.redirect('/tasks')

def todolistpath(task):
    dir_path = tasksdir
    officialtodo = '%s/%s/%s.todo' % (dir_path, task, task)
    try:
        os.stat(officialtodo)
        return officialtodo
    except OSError, e:
        pass
    try:
        # Could have an alternate todo file
        return glob.glob('%s/%s/*.todo' % (dir_path, task))[0]
    except IndexError, e:
        pass
    # still here? then let's go with the official path
    return officialtodo

class FutureeditURL:
    def GET(self, requestedtask):
        headerdata = getHeaderHTML()
        pagetitle = 'Editing Task %s' % requestedtask

        stringBuf = StringIO.StringIO()
        printtodolistDB(requestedtask, fh=stringBuf, backupmode=True)
        stringBuf.seek(0)
        content = stringBuf.read()
        if not content:
            content = '\n\nblah, blah, blah\n\n'

        print render.futureedit(headerdata, pagetitle, content, requestedtask, cache=False)

    def POST(self, requestedtask):
        input = web.input()
        if not loggedin():
            web.redirect('/future/%s' % requestedtask)
            return False
        filename = '.tt_web_%s_%s.tmp' % (requestedtask, time.strftime('%Y-%m-%d_%H:%M:%S'))
        fh = open(filename, 'w')
        fh.write(input.tododata)
        fh.close()
        updatetodolist(requestedtask, filename=filename)
        web.redirect('/future/%s' % requestedtask)

class FutureURL:
    def GET(self, requestedtask):
        headerdata = getHeaderHTML()
        pagetitle = ''
        futuredata = ''
        moreedits = ''
        cur_task = ''
        task_color = {}
        task_count = 0

        if requestedtask:
            todos = [t for t in Todos.select(Todos.q.task==requestedtask, orderBy=Todos.q.duedate) ]
            todos.reverse() # newest to oldest
            task_total = 0
            pagetitle = '<h3><a href="/future">TASK %s</a></h3>' % (requestedtask)

            N = 0
            for todo in todos:
                #epoch, task, title, body, duration, complete = todo
                if not todo.completed:
                    task_total += todo.duration
                if not task_color.has_key(todo.task):
                    task_color[todo.task] = color_samples[task_count % len(color_samples)]
                    task_count += 1
                completed_id = 'incomplete'
                if todo.completed:
                    completed_id = 'complete' #'text-decoration: line-through; '
                futuredata += '<li class="%s"><span class="todotitle" ondblclick="togglecomplete(this, %d);">%s</span>\n  <p class="tododuedate">%s</p>\n  <p class="todobody" id="%s_%d" ondblclick="edittodobody(this, %d);">%s</p>\n</li>\n' % \
                    (completed_id, todo.id, todo.title, todo.duedate.strftime('%Y-%m-%d %H:%M'), requestedtask, N, N, web.net.htmlquote(todo.body).replace('\n', '<br>\n'))
                N += 1
            futuredata = '<ol>\n%s</ol>\n' % futuredata

            pagetitle += '\n<h3>%s will take %d hours to complete.</h3>\n' % (requestedtask, task_total/60)

        else: # all tasks together
            todos = [t for t in Todos.select(orderBy=Todos.q.duedate) ]
            todos.reverse() # newest to oldest
            pagetitle = '<h3>Incomplete TODO Items from Each Task</h3>'
            for todo in todos:
                #epoch, task, title, body, duration, complete = todo
                if todo.completed:
                    continue
                if not task_color.has_key(todo.task):
                    task_color[todo.task] = color_samples[task_count % len(color_samples)]
                    task_count += 1
                futuredata += '<tr>\n  <td>%s</td>\n  <td><a style="color:%s;" href="/future/%s">%s</a></td>\n  <td onclick="editme(this, event);">%s</td>\n</tr>\n' % \
                              (todo.duedate.strftime('%Y-%m-%d %H:%M'), task_color[todo.task], todo.task, todo.task, todo.title)

            futuredata = '<table>\n%s</table>\n' % futuredata

            moreedits = '<h3>Start Planning TODO Items for These Tasks</h3>\n<table>\n'
            maxcolumns, columns = 5, 0
            # now for the tasks which have had no planning.
            for t in Tasks.select(orderBy=Tasks.q.task):
                if t.task not in task_color:
                    if not columns:
                        moreedits += '<tr>\n'
                    moreedits += '  <td><a href="/futureedit/%s">%s</a></td>\n' % (t.task, t.task)
                    columns += 1
                    if columns == maxcolumns:
                        moreedits += '</tr>\n'
                        columns = 0
            moreedits += '</table>\n'

        print render.future(headerdata, pagetitle, requestedtask, futuredata, moreedits, cache=False)

class BargraphURL:
    def GET(self, year1, month1, day1, year2, month2, day2):
        headerdata = getHeaderHTML()
        t1 = time.strptime('%s%s%s 12' % (year1, month1, day1), '%Y%m%d %H')
        t2 = time.strptime('%s%s%s 12' % (year2, month2, day2), '%Y%m%d %H')

        conditions = []
        conditions.append(Journal.q.start >= datetime.datetime(t1.tm_year, t1.tm_mon, t1.tm_mday, 0,0,0))
        conditions.append(Journal.q.start <= datetime.datetime(t2.tm_year, t2.tm_mon, t2.tm_mday, 23,59,59))

        title = 'Period starting on %s ending on %s' % (time.strftime('%F', t1), time.strftime('%F', t2))
        
        alltasks = {}
        bargraph = ''
        for j in Journal.select(AND(*conditions)):
            if not alltasks.has_key(j.task):
                alltasks[j.task] = 0
            alltasks[j.task] += j.duration

        try:
            colorN = 0
            sortedtasks = [ [y, x] for x, y in alltasks.items() ]
            sortedtasks.sort(reverse=True) # okay, now sorted
            max_width = 80 # in percent
            max_minutes = sortedtasks[0][0]
            shadeofred = 255
            red_step = 200 / len(sortedtasks)
            #print 'max_minutes = %d\n' % max_minutes
            for duration, task in sortedtasks:
                bargraph += '<p style="background-color:#%x0000; width:%s%%; border:solid;">%d hours working on task "%s"</p>\n' % \
                            (shadeofred, int(float(duration) / max_minutes * max_width) + 18, duration/60, task)
                colorN += 1
                shadeofred -= red_step
        except IndexError, e:
            pass
                
        print render.bargraph(headerdata, title, bargraph, cache=False)

class WeekViewURL:
    def GET(self, year, month, day):
        headerdata = getHeaderHTML()
        #print '<body>\n<html>\n'
        week = range(7)[weekstartson:] + range(7)[0:weekstartson]
        t1 = time.strptime('%s%s%s 12' % (year, month, day), '%Y%m%d %H')
        requestedday = time.mktime(t1)
        day_in_S = 86400 # 60*60*24
        #week_start = requestedday - (t1.tm_wday - weekstartson) * day
        week_start = requestedday - week.index(t1.tm_wday) * day_in_S
        ws = time.localtime(week_start)
        week_end = requestedday + (weekstartson + 6 - t1.tm_wday) * day_in_S
        we = time.localtime(week_end)

        #title = 'Summary for the week'
        tasklist = ''
        title = 'Week starting on %s ending on %s' % (time.strftime('%F',time.localtime(week_start)), time.strftime('%F',time.localtime(week_end)))
        #
        # Generating a dict of 'Task' -> list of weekly time spent per day
        # e.g. { 'MyFavTask': [0, 3, 0, 0, 4, 0, 1], ... }
        weeklytasks = {}
        weeklytasks['unaccounted'] = [0, 0, 0, 0, 0, 0, 0]
        weeklytasks['work day'] = [0, 0, 0, 0, 0, 0, 0]
        for i in range(7):
            #hrs = duration[week[i]]
            t1 = time.localtime((i * day_in_S) + week_start)

            tasks, clocks = getdaytasks(t1.tm_year, t1.tm_mon, t1.tm_mday)
            negative_time = sum([ j.duration for j in tasks if j.task.lower() in negative_tasks.split(' ') ])
            accounted_time = sum([ j.duration for j in tasks if j.task.lower() not in negative_tasks.split(' ') ])
            clockedin_time = sum([ (time.mktime(clocks[i*2 + 1]) - time.mktime(clocks[i*2]))/60 for i in range(len(clocks) / 2) ]) - negative_time

            weeklytasks['work day'][t1.tm_wday] = clockedin_time
            weeklytasks['unaccounted'][t1.tm_wday] = clockedin_time - accounted_time

            for j in tasks:
                if weeklytasks.has_key(j.task):
                    weeklytasks[j.task][t1.tm_wday] += j.duration
                else:
                    weeklytasks[j.task] = [0, 0, 0, 0, 0, 0, 0]
                    weeklytasks[j.task][t1.tm_wday] = j.duration

        if weeklytasks.has_key(unsure_task):
            weeklytasks['total %s' % unsure_task] = [ weeklytasks['unaccounted'][i] + weeklytasks[unsure_task][i] for i in range(len(weeklytasks['unaccounted'])) ]

        # first generate the table header
        taskmatrix_hdr = '<tr class="taskheader"><th>Task</th>'
        for i in range(7):
            t1 = time.localtime((i * day_in_S) + week_start)
            taskmatrix_hdr += '<th><a href="/dayof/%d/%02.d/%02.d">%s</a></th>' % (t1.tm_year, t1.tm_mon, t1.tm_mday, time.strftime('%a', t1))
        taskmatrix_hdr += '</tr>\n'
        taskmatrix = ''
        taskmatrix_end = ''
        counter = 0
        for task, duration in weeklytasks.iteritems():
            #taskmatrix +=  '%20s:\t%s' % (task, str(duration))
            total = sum(duration)
            if total:
                wtotal = ''
                for i in range(7):
                    hrs = duration[week[i]]
                    if hrs:
                        t1 = time.localtime((i * day_in_S) + week_start)
                        wtotal += '<td><a href="/dayof/%d/%02.d/%02.d">%.2f</a></td>' % (t1.tm_year, t1.tm_mon, t1.tm_mday, float(hrs)/60)
                    else:
                        wtotal += '<td></td>'
                if task == 'work day' or task == 'unaccounted' or task == 'total %s' % unsure_task:
                    taskmatrix_end += '<tr class="workday"><td>%s</td>%s<td>= %.2f hrs</td></tr>\n' % (task, wtotal, float(total)/60)
                else:
                    taskmatrix += '<tr class="d%d"><td>%s</td>%s<td>= %.2f hrs</td></tr>\n' % (counter % 2, task, wtotal, float(total)/60)
                    counter += 1
        taskmatrix += taskmatrix_end

        print render.weekview(headerdata, title, taskmatrix_hdr, taskmatrix, tasklist, cache=False)


def getclockdata(year, month, day):
    tasks, clocks = getdaytasks(year, month, day)

    __top = 80
    __top += 60
    __left = 50

    hour_begin = clocks[0].tm_hour
    hour_end = clocks[-1].tm_hour
    
    # now add some clocked in time indicators such as brackets and sum of day thus far...
    clockdata = ''
    for i in range(len(clocks) / 2):
        t1 = clocks[i*2]
        t2 = clocks[i*2 + 1]
        t1_left = __left + (t1.tm_hour - hour_begin) * pixels_per_hour + (t1.tm_min * pixels_per_hour) / 60
        t2_left = __left + (t2.tm_hour - hour_begin) * pixels_per_hour + (t2.tm_min * pixels_per_hour) / 60
        clockdata += '<p class="clockeddata" style="position:absolute; top:%dpx; left:%dpx; width:%dpx; height:%dpx;"></p>\n' % \
                   ( __top - 10, t1_left, t2_left - t1_left + 4, 5)

    return clockdata

    
def getdaytext(year, month, day):
    tasks, clocks = getdaytasks(year, month, day)
    negative_time = sum([ j.duration for j in tasks if j.task.lower() in negative_tasks.split(' ') ])
    accounted_time = sum([ j.duration for j in tasks if j.task.lower() not in negative_tasks.split(' ') ])
    clockedin_time = sum([ (time.mktime(clocks[i*2 + 1]) - time.mktime(clocks[i*2]))/60 for i in range(len(clocks) / 2) ]) - negative_time
    
    daytext = '<table>\n'
    for j in tasks:
        jt = time.strptime("%s" % j.start, '%Y-%m-%d %H:%M:%S')
        N = j.id

        daytext += '<tr>\n  <td id="T%d_text" onmouseover="addcolor(\'T%d\')" onmouseout="rmcolor(\'T%d\')"><b>%02d:%02d</b> %s [%dmin - %s]</td>\n' % \
                   (N, N, N, jt.tm_hour, jt.tm_min, j.description, j.duration, j.task)
        daytext += '  <td><form method="post" action="/deltask/%d"><input type="submit" value="delete" class="delete" onmouseover="addcolor(\'T%d\')" onmouseout="rmcolor(\'T%d\')"></form></td>\n</tr>\n' % (N, N, j.id)

    daytext += '</table>\n'        
    daytext = '<p class="clockedinfo">Worked %.2f hrs of which %.2f hrs are unaccounted for.</p>\n<div class="clear"></div>\n' % \
              (float(clockedin_time)/60, float(clockedin_time - accounted_time)/60) + daytext

    return daytext

class UpdateURL:
    def POST(self, task, delta):
        pixeldiff = int(delta)
        min_diff = float(pixeldiff) / pixels_per_hour * 60
        
        int_re = re.compile('[^0-9]*(\d+).*')
        id = int(int_re.findall(task)[0])
        j = Journal.get(id)
        t1 = time.strptime("%s" % j.start, '%Y-%m-%d %H:%M:%S')
        if loggedin():
            j.start = datetime.datetime(*time.localtime(time.mktime(t1) + (min_diff * 60))[:6])

        daytext = getdaytext(str(t1.tm_year), str(t1.tm_mon), str(t1.tm_mday))
        print daytext

class clockdataURL:
    def GET(self, task):

        int_re = re.compile('[^0-9]*(\d+).*')
        id = int(int_re.findall(task)[0])
        j = Journal.get(id)
        t1 = time.strptime("%s" % j.start, '%Y-%m-%d %H:%M:%S')
        
        clockdata = getclockdata(str(t1.tm_year), str(t1.tm_mon), str(t1.tm_mday))
        print clockdata

def getdaytasks(year, month, day):

    tasks = []
    clock_times = []
    for j in Journal.select(AND(Journal.q.start >= datetime.datetime(int(year), int(month), int(day), 0,0,0), Journal.q.start <= datetime.datetime(int(year), int(month), int(day), 23,59,59)), orderBy=Journal.q.start):
        jt = time.strptime("%s" % j.start, '%Y-%m-%d %H:%M:%S')
        if 'clock' in j.task.lower():
            clock_times.append(jt)
        tasks.append(j)

    # Now that we have recorded each clock event, now determine if they should be updated
    for j in tasks:
        if 'clock' in j.task.lower(): continue
        
        end = time.strptime("%s" % j.start, '%Y-%m-%d %H:%M:%S')
        begin = time.localtime(time.mktime(end) - (j.duration * 60))

        # does this task start before a clock in?
        clock_times.append(begin)
        clock_times.sort()
        idx = clock_times.index(begin)
        if idx % 2 == 0:
            if len(clock_times) - 1 == idx:
                clock_times.append(end)
                continue
            else:
                clock_times.pop(idx + 1)
        else:
            clock_times.remove(begin)

        # does this task end after a clock out?
        clock_times.append(end)
        clock_times.sort()
        idx = clock_times.index(end)
        # idx of 
        if idx % 2 == 0:
            clock_times.pop(idx - 1)
        else:
            clock_times.remove(end)

    # do I need to add a closing clockout?
    if len(clock_times) == 1:
        now = time.localtime()
        if now.tm_year == int(year) and now.tm_mon == int(month) and now.tm_mday == int(day):
            clock_times.append(time.localtime())
        else:
            clock_times.append(time.strptime("%s" % tasks[-1].start, '%Y-%m-%d %H:%M:%S'))
    
    return tasks, clock_times

class DayViewURL:
    def GET(self, year, month, day):
        headerdata = getHeaderHTML()

        tasks, clocks = getdaytasks(year, month, day)
        negative_time = sum([ j.duration for j in tasks if j.task.lower() in negative_tasks.split(' ') ])
        accounted_time = sum([ j.duration for j in tasks if j.task.lower() not in negative_tasks.split(' ') ])

        __top = 80
        __left = 50

        # Day header and the hour numbers
        t1 = time.strptime('%s%s%s 12' % (year, month, day), '%Y%m%d %H')
        yesterday = time.localtime(time.mktime(t1) - 86400) # 60*60*24
        tomorrow  = time.localtime(time.mktime(t1) + 86400) # 60*60*24
        dayheader = '<p class="dayheading"><a class="arrownav" href="/dayof/%s">&lt;</a><a href="/weekof/%d/%02.d/%02.d">%s %d-%02.d-%02.d</a><a class="arrownav" href="/dayof/%s">&gt;</a></p>\n' % \
                    (time.strftime('%F', yesterday).replace('-', '/'), t1.tm_year, t1.tm_mon, t1.tm_mday, time.strftime('%A', t1), t1.tm_year, t1.tm_mon, t1.tm_mday, time.strftime('%F', tomorrow).replace('-', '/'))
        if clocks:
            hour_begin = clocks[0].tm_hour
            hour_end = clocks[-1].tm_hour
        else:
            hour_begin = 8
            hour_end = 17

        small = 1
        for hour in range(hour_begin, hour_end+1):
            if small:
                font_size = 15
                top = __top + 0
            else:
                font_size = 22
                top = __top + 10
                
            dayheader += '<p style="position:absolute; top:%dpx; left:%dpx; font-size:%dpx;">%d</p>\n' % \
                         (top,__left + (hour - hour_begin) * pixels_per_hour, font_size, hour)
            small = (small + 1) % 2
        __top += 60 # making room for the next set of absolute objects
        
        # now add some clocked in time indicators such as brackets and sum of day thus far...
        clockdata = ''
        clockedin_time = 0
        for i in range(len(clocks) / 2):
            t1 = clocks[i*2]
            t2 = clocks[i*2 + 1]
            clockedin_time += (time.mktime(t2) - time.mktime(t1)) / 60 # minutes
            t1_left = __left + (t1.tm_hour - hour_begin) * pixels_per_hour + (t1.tm_min * pixels_per_hour) / 60
            t2_left = __left + (t2.tm_hour - hour_begin) * pixels_per_hour + (t2.tm_min * pixels_per_hour) / 60
            clockdata += '<p class="clockeddata" style="position:absolute; top:%dpx; left:%dpx; width:%dpx; height:%dpx;"></p>\n' % \
                       ( __top - 10, t1_left, t2_left - t1_left + 4, 5)
        clockedin_time -= negative_time

        daydata = ''
        daytext = '<table>\n'
        maxheight = 100
        pseudotask_height = 33 * 3
        cssdata = ''

        # Empty box to drag into the scene indicating a new task.
        left = 0 #__left - pixels_per_hour
        daydata += '<p id="%s" class="newtask" onmousedown="dragNewOBJ(this,event); return false;" style="position:absolute; border:solid; top:%dpx; left:%dpx; width:%dpx; height:%dpx;"></p>\n' % \
                   ('newtaskon/%04d/%02d/%02d' % (int(year), int(month), int(day)), __top, left, 10, pseudotask_height)
        
        for j in tasks:
            jt = time.strptime("%s" % j.start, '%Y-%m-%d %H:%M:%S')
            N = j.id

            left = __left + (jt.tm_hour - hour_begin) * pixels_per_hour + (jt.tm_min * pixels_per_hour) / 60
            width = (j.duration * pixels_per_hour) / 60
            height = width * 3
            if height > 200:
                height = int(log(height) / 7 * 300)
            if height > maxheight:
                maxheight = height

            if 'clock' in j.task.lower():
                width = 0
                height = pseudotask_height

            daydata += '<p id="T%d_data" onmouseover="addcolor(\'T%d\')" onmouseout="rmcolor(\'T%d\')" onmousedown="dragOBJ(this,event); return false;" style="position:absolute; border:solid; top:%dpx; left:%dpx; width:%dpx; height:%dpx;"></p>\n' % \
                       (N, N, N, __top, left - width, width, height)
            daytext += '<tr>\n  <td id="T%d_text" onmouseover="addcolor(\'T%d\')" onmouseout="rmcolor(\'T%d\')"><b>%02d:%02d</b> %s [%dmin - %s]</td>\n' % \
                       (N, N, N, jt.tm_hour, jt.tm_min, j.description, j.duration, j.task)
            daytext += '  <td><form method="post" action="/deltask/%d"><input type="submit" value="delete" class="delete" onmouseover="addcolor(\'T%d\')" onmouseout="rmcolor(\'T%d\')"></form></td>\n</tr>\n' % (N, N, j.id)

        daytext += '</table>\n'
            
        daytext = '<p class="clockedinfo">Worked %.2f hrs of which %.2f hrs are unaccounted for.</p>\n<div class="clear"></div>\n' % \
                  (float(clockedin_time)/60, float(clockedin_time - accounted_time)/60) + daytext

        cssdata += 'div#daytext { position: absolute; top: %dpx; }' % (int(maxheight + __top))
        #daytext = getdaytext(year, month, day)
        print render.dayview(cssdata, headerdata, dayheader, clockdata, daydata, daytext, cache=False)
        
def createTables():
    tables = [Tasks, Journal, Todos, User, Session]
    for table in tables:
        try:
            #print repr(table)
            table.createTable()
        except Exception, e:
            pass        

def generateTasks(dir_path):
    dirTasks = [ d for d in os.listdir(dir_path) if os.path.isdir(dir_path + os.sep + d) ]
    for t in Tasks.select(orderBy=Tasks.q.task):
        if t.task in dirTasks:
            dirTasks.remove(t.task)
    #print repr(dirTasks)
    for newproject in dirTasks:
        Tasks(task=newproject, start=DateTimeCol.now())

def dumpTodos(dir_path, requestedtask='*'):
    all_todos = {}
    for path in glob.glob('%s/%s/*.todo' % (dir_path, requestedtask)):
        todo = parsetodolist(path, os.path.basename(os.path.dirname(path)))
        if todo:
            all_todos[os.path.basename(os.path.dirname(path))] = todo
    return all_todos

def printTodos(all_todos):
    sep = ''
    for task, todo in all_todos.items():
        print '%s*** %s ***\n%s' % (sep, task, '-' * 70)
        printtodolist(todo)
        sep = '\n'

def timesortTodos(all_todos):
    sorted_todos = []
    for task, todos in all_todos.items():
        for i in range(len(todos)):
            duedate, taskname, title, body, tasktime, completed = todos[i]
            #if completed:
            #    continue
            sorted_todos.append(todos[i])
            
    sorted_todos.sort()
    return sorted_todos

def dateparse(date):
    epoch = 0
    for format in formats:
        try:
            t1 = time.strptime(date, format)
            
            # massage the date to be relative to now, when necessary
            t2 = list(t1)
            fields = [ format[i+1] for i in range(0,len(format)) if format[i] == '%' ]
            now = time.localtime()
            if 'Y' not in fields and 'y' not in fields: t2[0] = now[0] # fix year
            if 'm' not in fields: t2[1] = now[1] # fix month
            if 'd' not in fields: t2[2] = now[2] # fix day
            if 'H' not in fields: t2[3] = now[3] # fix hour
            if 'M' not in fields: t2[4] = now[4] # fix minute
            if 'S' not in fields: t2[5] = now[5] # fix seconds
            epoch = time.mktime(t2)
            
            break
        except (Exception), e:
            continue
    return epoch

def shellescape(s):
    shell_special_chars = '\\\'`()$"!*&#;{}|<>' # leave the \ first in the string
    for c in shell_special_chars:
        s = s.replace(c, '\\' + c)
    return s

def lstasks(epoch, all=0, task=None, backupmode=False):

    weekstartson=0 # mon=0, tue=1, wed=2, thr=3, Fri = 4, Sat=5, Sun=6
    t1 = time.localtime(epoch)
    day = 86400 # 60*60*24
    wk_start = time.localtime(epoch - (t1.tm_wday - weekstartson) * day)
    wk_end = time.localtime(epoch + (weekstartson + 7 - t1.tm_wday) * day)

    conditions = []
    if task: conditions.append(Journal.q.task==task)
    
    if not all:    # today
        conditions.append(Journal.q.start >= datetime.datetime(t1.tm_year, t1.tm_mon, t1.tm_mday, 0,0,0))
        conditions.append(Journal.q.start <= datetime.datetime(t1.tm_year, t1.tm_mon, t1.tm_mday, 23,59,59))
    elif all == 1: # week
        conditions.append(Journal.q.start >= datetime.datetime(wk_start.tm_year, wk_start.tm_mon, wk_start.tm_mday, 0,0,0))
        conditions.append(Journal.q.start <= datetime.datetime(wk_end.tm_year, wk_end.tm_mon, wk_end.tm_mday, 23,59,59))
    
    for j in Journal.select(AND(*conditions), orderBy=Journal.q.start):
        if backupmode:
            print 'tt.py %s %s %s -d \'%s\' # id %d' % (j.task, j.duration, shellescape(j.description), j.start, j.id)
        else:
            print '(%d) %s: Worked on %s for %s minutes: %s' % (j.id, j.start, j.task, j.duration, j.description)

def timeshift(epoch, delta_minutes):
    # FIXME: needs to take into account that I'd like to work only on business hours.
    return epoch + (delta_minutes * 60)

def parsetodolist(filepath, taskname):
    fh = open(filepath, 'r')

    title_re = re.compile('\s*\d+\.\s*(\w+.*)')
    date_re = re.compile('\d{4}-\d{1,2}-\d{1,2}')
    iscompleted_re = re.compile('(?:done|finished|completed?)!', re.I)
    hour_re = re.compile('(-?\d+)\s*hrs?')
    minute_re = re.compile('(-?\d+)\s*min(?:utes?)?')
    day_re = re.compile('(-?\d+)\s*days?')

    title = ''
    body = ''
    tasktime = 0
    completed = 0
    duedate = 0
    nextstarttime = 0
    default_duedate = int(time.time()) + 604800 # you get a week (60*60*24*7) to complete this *when a default is needed*

    # returning 'tasks'; list of list for each numbered task in the todo file (see .append() for fields)
    tasks = []
    for line in fh:
        if title_re.match(line):
            if title:
                # done parsing the previous task, now let's add it.
                if not tasktime:
                    tasktime = 60 # average task (min)
                if duedate:
                    nextstarttime = timeshift(duedate, transitiontime)
                elif nextstarttime:
                    duedate = timeshift(nextstarttime, tasktime)
                    nextstarttime = timeshift(duedate, transitiontime)
                tasks.append([duedate, taskname, title, body, tasktime, completed])
            
            # New titled todo
            title = title_re.findall(line)[0]
            # reset task variables to defaults
            body = ''
            tasktime = 0
            duedate = 0
            completed = 0
        else:
            body += line # body text of the task
        
        hrs = sum([ int(x) for x in hour_re.findall(line) ])
        minutes = sum([ int(x) for x in minute_re.findall(line) ])
        days = sum([ int(x) for x in day_re.findall(line) ])
        tasktime += minutes + 60*hrs + (7.75 * 60 * days)

        completed += len(iscompleted_re.findall(line))
        if date_re.search(line):
            try:
                duedate = int(time.mktime(time.strptime(date_re.findall(line)[0] + ' 12:00' , '%Y-%m-%d %H:%M')))
            except (ValueError), e:
                # problem converting their date, such as specifying 31st day in September
                # getting default duedate of one week
                duedate = default_duedate

    fh.close()
    if title:
        if not tasktime:
            tasktime = 60 # average task (min)
        if not duedate and nextstarttime:
            duedate = timeshift(nextstarttime, tasktime)
            
        tasks.append([duedate, taskname, title, body, tasktime, completed])

    # now fill in first few tasks before the first explicit due date specified
    if not nextstarttime:
        nextstarttime = long_future
    duedate_idx = 0
    tasktime_idx = 4
    for i in range(len(tasks)-1, -1, -1):
        if not tasks[i][duedate_idx]:
            tasks[i][duedate_idx] = timeshift(nextstarttime, -transitiontime)
            nextstarttime = timeshift(tasks[i][duedate_idx], -tasks[i][tasktime_idx])
        else:
            nextstarttime = timeshift(tasks[i][duedate_idx], -tasks[i][tasktime_idx])

    return tasks

def printtodolist(todolist):
    for i in range(len(todolist)):
        duedate, taskname, title, body, tasktime, completed = todolist[i]
        if completed:
            N = 'X'
        else:
            N = str(i+1)
        dueby = ''
        if duedate:
            dueby = time.strftime(' Due by %Y-%m-%d %H:%M.', time.localtime(duedate))
            
        print '%2s. %s' % (N, title)
        if completed:
            print '    Completed'
        else:
            print '    Should take %d minutes to complete.%s' % (tasktime, dueby)

class edittodolistURL:
    def POST(self, task, idx):
        input = web.input()
        newtask = input.todoparagraph
        #print newtask
        if loggedin():
            print edittodolist(task, idx, newtask)

def edittodolist(task, idx, newbody):
    todos = [t for t in Todos.select(Todos.q.task==task, orderBy=Todos.q.duedate) ]
    todos[int(idx)].body = newbody.replace('<br>','')
    todos[int(idx)].modifydate = datetime.datetime(*time.localtime()[:6])
    return newbody

class updatetodoURL:
    def POST(self, action, id):
        if not loggedin():
            print 'Not logged in.'
            return False
        try:
            todo = Todos.get(int(id))
            if action == 'completed':
                todo.completed = True
            elif action == 'incomplete':
                todo.completed = False
            else:
                print 'Unknown action to update Todo ID: %s' % id
                return False
        except (SQLObjectNotFound, IndexError, ValueError), e:
            pass
        return True

def istask(task):
    # for now, I associate a task with a local dir (helps for bash completions)
    # may later use the DB
    try:
        if S_ISDIR(os.stat(tasksdir + os.sep + task)[0]):
            return True
    except (IndexError, OSError), e:
        return False

def printtodolistDB(task, fh=sys.stdout,  backupmode=False, all=0):
    n=0
    conditions = []
    if not all: conditions.append(Todos.q.task==task)
    for todo in Todos.select(AND(*conditions), orderBy=Todos.q.duedate):
        #task, title, body, submitdate, modifydate, duedate, duration, completed, journal = todo
        n += 1

        if backupmode:
            fh.write('%d. %s\n   %s\n' % (n, todo.title, todo.body.strip()))
            #if todo.completed:
            #    fh.write('   Due by %s Completed!\n\n' % todo.duedate.strftime('%F %H:%M'))
            #else:
            #    fh.write('   Due by %s Incomplete\n\n' % todo.duedate.strftime('%F %H:%M'))
        else:
            N = str(n)
            if todo.completed: N = 'X'

            fh.write('%2s. %s\n   %s\n' % (N, todo.title, todo.body.strip()))
            if todo.completed:
                completedTXT = 'Completed'
            else:
                completedTXT = 'Incomplete'
            metadata = []
            metadata.append('Task is %s. Due By %s' % (completedTXT, todo.duedate.strftime('%F %H:%M')))
            metadata.append('Estimated to take %d minutes to complete' % todo.duration)
            metadata.append('Created on %s' % todo.submitdate.strftime('%F %H:%M'))
            metadata.append('Last updated on %s' % todo.modifydate.strftime('%F %H:%M'))
            maxlength = max([len(s) for s in metadata])
            fh.write('   ' + '*' * (maxlength + 4) + '\n')
            for s in metadata:
                fh.write('   * %s' % s)
                fh.write(' ' * (maxlength - len(s)) + ' *\n')
            fh.write('   ' + '*' * (maxlength + 4) + '\n\n')

def updatetodolistsingle(duedate, task, minutes, description):

    now = datetime.datetime(*time.localtime()[:6])
    dueby = datetime.datetime(*time.localtime(dateparse(duedate))[:6])
    todosDB = []
    titlesDB = []
    for todo in Todos.select(Todos.q.task==task):
        #todo.delete(todo.id) # no, we're not completely like crontab(1)
        titlesDB.append(todo.title.strip())
        todosDB.append(todo)

    if description.strip() in titlesDB:
        todoDB = todosDB[titlesDB.index(description.strip())]
        todoDB.duedate = dueby
        todoDB.tasktime = int(minutes)
        #todoDB.completed = completed != 0
        todoDB.modifydate = now
        todoDB.journal = ""
        #todoDB.body = body
    else:
        Todos(task=task, title=description, body='\nEntered via commandline.\n', submitdate=now, modifydate=now, duedate=dueby, duration=int(minutes), createdfrom='commandline', completed=False, journal="")


def updatetodolist(task, filename=''):
    # Todos Fields: task, title, body, submitdate, modifydate, duedate, duration, journal
    if not loggedin(): return False

    needtoremovefile = False
    createdfrom = filename
    if not filename:
        print 'edit %s\'s future' % task
        # Using the 'crontab' style of using your VISUAL or EDITOR var to generate a file should set the filename arg
        editor = os.getenv('VISUAL')
        if not editor: editor = os.getenv('EDITOR', 'vi')
        filename = '.tt_editor_%s_%s.tmp' % (task, time.strftime('%Y-%m-%d_%H:%M:%S'))
        fh = open(filename, 'w')
        printtodolistDB(task, fh, backupmode=True)
        fh.close()
        os.system('%s %s' % (editor, filename))
        needtoremovefile = True
        createdfrom = 'editor'
    else:
        print 'update %s\'s future via file contents of "%s". gotcha.' % (task, filename)
        if filename.find('.tt_web_') != -1:
            createdfrom = 'web'

    todosDB = []
    titlesDB = []
    for todo in Todos.select(Todos.q.task==task):
        #todo.delete(todo.id) # no, we're not completely like crontab(1)
        titlesDB.append(todo.title.strip())
        todosDB.append(todo)

    todos = parsetodolist(filename, task)
    for todo in todos:
        duedate, taskname, title, body, tasktime, completed = todo
        now   = datetime.datetime(*time.localtime()[:6])
        dueby = datetime.datetime(*time.localtime(duedate)[:6])

        if title.strip() in titlesDB:
            todoDB = todosDB[titlesDB.index(title.strip())]
            if body.strip() == todoDB.body.strip(): # nice use of variable name + function call
                continue # didn't update this item...
            todoDB.duedate = dueby
            todoDB.tasktime = int(tasktime)
            todoDB.completed = completed != 0
            todoDB.modifydate = now
            todoDB.journal = ""
            todoDB.body = body
        else:
            Todos(task=task, title=title, body=body, submitdate=now, modifydate=now, duedate=dueby, duration=int(tasktime), createdfrom=createdfrom, completed=completed != 0, journal="")

    if needtoremovefile:
        os.remove(filename)

def addtask(sdate, task, minutes, description):
    epoch = dateparse(sdate)
    if epoch:
        t1 = time.localtime(epoch)
        #print 'Parsed date "%s" to -> "%s"' % (sdate, time.strftime('%c', t1))
        Journal(task=task, start=datetime.datetime(*t1[:6]), duration=minutes, description=description)
    else:
        print 'Invalid date specification "%s" used.' % options.date
        #sys.exit(1)
    
if __name__ == '__main__':

    #todo = parsetodolist(sys.argv[1], 'blah')
    #printtodolist(todo)
    #sys.exit(0)

    #edittodolist(sys.argv[1], 1, 'blah, blah, blah') # e.g. "RFS1406"

    #uri = 'sqlite:///home/jon/scripts/timetracker/tt.db'
    #dbfile = '%s/tt.db' % (os.sep.join(sys.argv[0].split(os.sep)[:-1]))

    if os.name == 'nt':
        # Windows style pathing for sqlobject: sqlite:///E|/scripts/timetracker/tt.db
        dbfile = '/%s/tt.db' % REL_DIR.replace(':\\', '|/').replace('\\', '/')
    else:
        dbfile = '%s%stt.db' % (REL_DIR,os.sep)

    uri = 'sqlite://%s' % (dbfile)
    #print 'uri = %s' % uri

    connection = connectionForURI(uri)
    sqlhub.processConnection = connection

    #Tasks.createTable()
    #Todos.dropTable()
    createTables()

    #Tasks(task='RFS1374', start=DateTimeCol.now())

    #todos = dumpTodos(REL_DIR)
    #printTodos(todos)
    #sortedtodos = timesortTodos(todos)
    #for todo in sortedtodos:
    #    print todo
    
    #print repr(Tasks.get(1))
    #print repr(Journal.get(406))
    #sys.exit(0)
    #print repr(Tasks.get(

    from optparse import OptionParser
    USAGE = """Usage: %s task minutes description [more description] [options]

Valid date format supported include:
\"%s\"""" % \
            (os.path.basename(sys.argv[0]), '", "'.join(formats))    
    parser = OptionParser(usage=USAGE)
    parser.add_option("-l", "--listtodaytasks", action="store_true", dest="listtodaytasks", default=False,
                      help="list out today's tasks")
    parser.add_option("-a", "--alltasks", action="count", dest="alltasks", default=False,
                      help="apply action to all tasks for the particular week (list twice to mean all-all, beyond this week)")
    parser.add_option("-r", "--remove", dest='id',
                      help="remove an ID from the journal")
    parser.add_option("-d", "--date", dest='date', default=time.strftime('%H:%M'),
                      help="manually set the date to be used")
    parser.add_option("-f", "--future", action="store_true", dest="future", default=False,
                      help="set in the future as in a TODO item")
    parser.add_option("-b", "--backup", action="store_true", dest="backup", default=False,
                      help="backup your data")
    parser.add_option("-e", "--edit", action="store_true", dest="edit", default=False,
                      help="edit either future content or specific journaled ID")
    parser.add_option("--taskdir", dest="tasksdir", default='%s%stasks' % (REL_DIR, os.sep),
                      help="change the base directory where I expect to see the directory representation of your tasks")
    parser.add_option("--user", dest="user",
                      help="define a new user for web authorization or update password")
    parser.add_option("--pam", dest="pam",
                      help="enable PAM for authentication and choose with service file to use.")

    (options, args) = parser.parse_args()
    tasksdir = options.tasksdir
    generateTasks(tasksdir)

    #print 'DEBUG: args: "%s" file: "%s"\nREL_DIR="%s", os.getcwd() = "%s"' % ('", "'.join(args), file, REL_DIR, os.getcwd())

    epoch = dateparse(options.date)
    if not epoch:
        print 'Invalid date specification "%s" used.' % options.date
        sys.exit(2)

    # Use PAM for password authentication?
    if options.pam:
        try:
            pam = __import__('pam')
            pam_service = options.pam
        except ImportError, e:
            print 'Error: Can not import "pam" module. Ensure you have the module installed. Using basic tt.py auth.'

    # Run the web server if we have only one argument specifying the port and/or other argument (default 8080)
    if len(args) == 0 and not options.listtodaytasks and not options.id and not options.edit and not options.user:
        print 'Starting web server on port %d' % 8080
        [ sys.argv.pop() for dummy in range(len(sys.argv)-1) ]
        os.chdir(REL_DIR)
        web.run(urls, globals())
    elif len(args) == 1:
        try:
            port = int(args[0])
            print 'Starting web server on port %d' % port
            os.chdir(REL_DIR)
            web.run(urls, globals())
        except ValueError, e:
            pass

    if options.user:
        try:
            user = User.selectBy(username=options.user).getOne()
            p = getpass.getpass('Setting new password for user "%s": ' % user.username)
            user.password = p
        except (main.SQLObjectNotFound), e:
            p = getpass.getpass('New user "%s". Please assign a password: ' % options.user)
            User(username=options.user, password=p)

    elif options.listtodaytasks:
        if options.future:
            if len(args) == 0 or not istask(args[0]):
                print 'Error: Need to tell me which TASK you\'d like to view future tasks for.'
                sys.exit(1)
            task = args[0]
            printtodolistDB(task, backupmode=options.backup)
        else:
            if len(args) > 0:
                lstasks(epoch, all=options.alltasks, task=args[0], backupmode=options.backup)
            else:
                lstasks(epoch, all=options.alltasks, backupmode=options.backup)
    elif options.id:
        try:
            j = Journal.get(options.id)
            print 'DELETING: (%d) %s: Worked on %s for %s minutes: %s' % (j.id, j.start, j.task, j.duration, j.description)
            j.delete(options.id)
        except SQLObjectNotFound, e:
            print 'Sorry, but id %s doesn\'t exist. Review the listings again.' % options.id

    elif options.edit:
        if options.future:
            if len(args) == 0 or not istask(args[0]):
                print 'Error: Need to tell me which TASK you\'d like to work on updating.'
                sys.exit(1)
            task = args[0]
            file = ''
            try:
                if S_ISREG(os.stat(args[1])[0]): file = args[1]
                # ala: tt.py task -ef filename
            except (IndexError, OSError), e:
                pass
            #print 'DEBUG: args: "%s" file: "%s"\nREL_DIR="%s", os.getcwd() = "%s"' % ('", "'.join(args), file, REL_DIR, os.getcwd())
            #sys.exit(0)

            updatetodolist(task, file)
            printtodolistDB(task, all=options.alltasks)
        else:
            try:
                id = sys.argv[sys.argv.index('-e') + 1]
                j = Journal.get(id)
                args.pop(args.index(id))
                j.task, j.duration, j.description = (args[0], int(args[1]), " ".join(args[2:]))
                if '-d' in sys.argv:
                    epoch = dateparse(options.date)
                    if epoch:
                        t1 = time.localtime(epoch)
                        j.start = datetime.datetime(*t1[:6])
                    else:
                        print 'Invalid date specification "%s" used. Leaving unmodified.' % options.date

                print 'UPDATING: (%d) %s: Worked on %s for %s minutes: %s' % (j.id, j.start, j.task, j.duration, j.description)
            except (SQLObjectNotFound, IndexError, ValueError), e:
                print 'Sorry, but either %s doesn\'t exist. Or you haven\'t specify the normal <task> <min> <description> arguments.\n%s' % (id, USAGE)
    else:
        try:
            curtask, minutes, description = (args[0], int(args[1]), " ".join(args[2:]))
            if options.future:
                #pass
                updatetodolistsingle(options.date, curtask, minutes, description)
                #(dueby, task, minutes, description)
            else:
                addtask(options.date, curtask, minutes, description)
        except (IndexError, ValueError), e:
            print '%s' % USAGE
            sys.exit(1)
