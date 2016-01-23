#Howto Guide in Recording Current Worked Tasks

# Introduction #

This is a quick guide in entering current activities via the command line.

# Details #
If you have not already, start with the InstallGuide so you can use bash command completion available to the `tt.py`. This means that after typing tt.py, hitting TAB TAB will show all of your current projects and starting to type one of them and hitting TAB again will complete the word.

The command line usage can be seen by running `tt.py --help`. The general syntax is:

`tt.py task minutes description [more description] [options]`

## Here are some examples ##

Simple Usage:
  * General recording of a 30 minute task on the rorlinux project.
> > `$ tt.py rorlinux 30 Meeting with Randy`
  * Clock in/out
> > `$ tt.py clock 0 Arrving. -d 07:17`
  * Outside events, such as night page
> > `$ tt.py breakfix 50 blast page concerning TOPS`
  * List Work today, this week, or all - all
> > `$ tt.py -l     $ tt.py -la     $ tt.py -laa`
  * List just the work for taskX such as `holiday`.
> > `$ tt.py holiday -laa`