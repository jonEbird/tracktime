#Install guide for Tracktime

# Linux / Unix Install Guide #

## Grab Necessary Packages ##

Fedora yum -y install:
```
  python-formencode
  python-sqlite2
  python-sqlobject
  python-setuptools-devel
```

Ubuntu sudo apt-get install:
```
  python
  python-pysqlite2
  sqlite
  python-sqlobject
```

## Setup the Command Completion ##

  1. Checkout from source for now. Don't want to maintain packages yet.
```
svn checkout http://tracktime.googlecode.com/svn/trunk/ ~/tracktime/
```
  1. Change directories to that newly created directory.
```
cd ~/tracktime/
```
  1. Setup Bash Command Completion. Then copy & paste the following line for updating your .bashrc:
```
echo "source $(pwd)/completion.bash $(pwd)/" >> ~/.bashrc
```

## Dry Run & DB Initialization ##
  1. Source your newly updated ~/.bashrc file (gets your PATH updated)
```
source ~/.bashrc
```
  1. Init your DB
```
tt.py --initdb=~/tracktime/tt.db
```
  1. Quick test. With a brand new DB, you will see nothing, but no errors.
```
tt.py -l
```

## Prepare Backups ##

  1. Staying within the same project directory, as created above in 2a, create a .backup directory.
```
mkdir .backup
```
  1. Now add the following line to your crontab
```
crontab -l > crontab.tmp
printf "# Backup your TrackTime data\n55 * * * * $(pwd)/backup.sh\n" >> crontab.tmp
crontab crontab.tmp
```

# Windows Install #

I have not done a lot of testing on windows, but have built in support for Windows. Since the script is pure python, support of Windows is primarily the use of `os.sep` as well as special handling of the sqlite URI used by the `sqlobject` module.

Okay, so what that all means is Tracktime does work on Windows. You will need to install sqlite for Windows. My recommendation is to firstly install the python module `setuptools` and afterwards use the `easy_install` to install the necessary modules:
```
sqlobject
formencode
pysqlite2
```

# USB Stick #

I have also tested using Tracktime on a portable USB stick. You need to start with [Portablepython](http://www.portablepython.com/) and then simply follow the same procedure as the Windows Install.

Eventually, I think running off a USB stick is the best option since you'll always have your time data with you.