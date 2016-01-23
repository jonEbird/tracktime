#Howto Guide in Using Natural Language to Specify Datetime

# Introduction #

With the command line, there are two available ways to specify a date and time. The most basic method is to
use the `-d` option and specify your datetime in one of the supported, formal methods.
Whenever you do not use the `-d` option, tracktime will attempt to gather the datetime from the text used on the commandline.

# Quick Examples #

The attempt in being able to support a natural language for specifying your datetime is that you should be able to use it naturally.
In that spirit, let's just right into some examples:
  * `tt.py -l yesterday`
  * `tt.py reports 60 Need to complete monthend reports for boss by Friday -f`
  * `tt.py breakfix 45 Late night support call last sun at 20:50`
  * `tt.py reports 20 Fill out timesheet tomorrow at COB -f`

Hopefully you get the idea.

# Details #

When the natural language parser is used, it starts with the current datetime. It then uses patterns, it knows about, to make
adjustments to the date. That means if you use the words "tomorrow" and "yesterday" in the same line, they would cancel each other out.

Officially, here are the different types of natural language you can specify:
  * "tomorrow" - Obvious. Adds one day.
  * "yesterday" - Obvious again. Subtracts one day.
  * "XX days ago" - With "XX" being digits, you can specify how many days ago.
  * "XX days" - Would typically use "in 3 days" but the "in" is not required.

All future forms, where you are targeting the day of the week.
Days of the week can be spelled out or abbreviated with the typical three character:
  * "next UNIT"
  * "by UNIT"
  * "this UNIT"
Besides UNIT being a day of the week, it can also be: "week", "month", "year" or "quarter"

Just as the previous future forms, you can use similar UNITs for past events via:
  * "last UNIT"

Sticking with the UNIT topic, finally, you can you use "on UNIT" which attempts to be smart about going into the future or past
when specifying a day of the week. So, if it current Wednesday and you specify "on tue" then we're moving backwards a day.
Conversely, saying "on friday" we would fast forward 2 days.

The rest of the supported forms are used for targeting the time of day:
  * "noon" - 12:00 am
  * "cob" or "close of business" - 17:00
  * "end" or "end of day" - 17:00
  * "HH:MM" - where "HH" and "MM" are digits specifying the military hour and minute.

Finally, feel free to use combinations of these today.
`tt.py report 60 Write more tracktime documentation next month on sat`