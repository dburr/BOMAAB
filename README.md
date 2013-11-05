# BOMAAB - APPs are Boarding

This guide will describe a setup for self-hosted, always-updated download/IAP statistics visualized by [Panic's Status Board](http://www.panic.com/statusboard/).

## Requirements:
- server with Java, MySQL, Bash, PHP, Cron
- Apple developer account
- StatusBoard APP

## tl;dr

- copy <tt>update.sh</tt>, <tt>index.php</tt> and <tt>db.php</tt> to a folder of your web server
- download and decompress [Autoingestion](http://apple.com/itunesnews/docs/Autoingestion.class.zip) to that folder
- create file `Autoingestion.properties` with your iTC login and password info
- create the MySQL table described under "MySQL setup"
- open <tt>update.sh</tt> and enter your credentials in the header, enter them again in <tt>db.php</tt>  (note: if you don't wish to use your normal iTunes Connect user/password, you can create a "sales-only" sub-user with a different password)
- run update.sh manually and check if everything runs fine; create a crontab entry for regular updates
- open Status Board on your iPad, create a new "Graph", enter the URL to your webserver's folder

Enjoy your downloads!

<img src="https://raw.github.com/omichde/BOMAAB/master/screen.jpg">

# Setup

MacMini with OS-X Server and DynDNS is running fine for me even on a DSL connection but YMMV. For BOMAAB OS-X Server can easily be replaced by [MAMP](http://www.mamp.info/), upgrading to PRO gives you a nice graphical installer and control app. Although I have installed [MySQL](http://www.mysql.com/downloads/mysql/) from the original package I prefer [Sequel Pro](http://www.sequelpro.com) for data retrieval and management a lot - this tool is amazing! Apart from the Terminal I use [TextMate](http://macromates.com) for editing and [Cronnix](http://code.google.com/p/cronnix/) to edit my crontab - yes, I confess, I'm a visual coder, not a Terminal hacker.

# 1. Step: Importing reports into a local database

In the [APP Store Reporting Instructions](http://www.apple.com/itunesnews/docs/AppStoreReportingInstructions.pdf) Apple provides the link to the Autoingestion class. This Java class will be used to download the daily reports, which are initially stored as a CSV file and imported later into a MySQL database.

Autoingestion.class now requires that the iTunes Connect username and password
be placed in a properties file.  Create a file `Autoingestion.properties` with
the following contents:

```
userID = your-apple-id
password = your-password
```

Note: If you don't wish to use your normal iTunes Connect user/password, you can create a "sales-only" sub-user with a different password.

Create a folder anywhere you like for downloading the reports regularly, copy <tt>update.sh</tt> into this folder and open it to configure various options.

	APPLEVENDORID="your-vendor-id"

This number can be found in [itunesconnect](https://itunesconnect.apple.com) under "Sales and Trends". In the headline, after your login name, the number like <tt>80012345</tt> is your Vendor ID.

	MYSQLUSER="your-mysql-username"
	MYSQLPASSWORD="your-mysql-password"

This is your user name and password for the MySQL database. The downloaded daily reports will partially be stored into your MySQL table.

	LOGDIR="$HOME/Library/Logs"

Set this to where you want the log file placed.  The default is fine for OS X; Linux/\*BSD users may want to set this to `/var/log` or something else.

	OSXDATE="YES"

Set this to YES if your `date` command supports the `-v` flag to calculate and print dates in the past (run `man date` to find out if yours does or not.  Most Linux/`*BSD variants don't.)

	REQUIRES_LOCAL_INFILE="NO"

Set this to "YES" if your `mysqld` requires the `--local-infile=1` flag.  If you run the script but get the error `The used command is not allowed with this MySQL version` then yours does.  Note that if this is the case, you will also need to modify the `mysqld` configuration file.  Edit the file `/etc/my.cnf` and in the `[mysqld]` section, ensure that the line `local-infile=1` is present.  (if it isn't, or the value is set to something other than `1`, add/change it appropriately.)

## MySQL setup

The scripts assume a database called <tt>itunesconnect</tt> with a table called <tt>sales</tt>. Its structure is closely modeled after the reports file format. Create the table with the following SQL command:

	CREATE TABLE `sales` (
	  `Provider` varchar(255),
	  `ProviderCountry` varchar(255),
	  `SKU` varchar(255),
	  `Developer` varchar(255),
	  `Title` varchar(255),
	  `Version` varchar(255),
	  `ProductTypeIdentifier` varchar(255),
	  `Units` int(11) NOT NULL,
	  `DeveloperProceeds` float NOT NULL,
	  `BeginDate` date NOT NULL,
	  `EndDate` date NOT NULL,
	  `CustomerCurrency` varchar(255),
	  `CountryCode` varchar(255),
	  `CurrencyOfProceeds` varchar(255),
	  `AppleIdentifier` varchar(255),
	  `CustomerPrice` float NOT NULL,
	  `PromoCode` varchar(255),
	  `ParentIdentifier` varchar(255),
	  `Subscription` varchar(255),
	  `Period` varchar(255)
	) ENGINE=MyISAM DEFAULT CHARSET=utf8;

## Synopsis: update.sh [YYYYMMDD]

The <tt>update.sh</tt> script accepts one optional parameter: the date for which to download and import the report in the format YYYYMMDD. If no parameter was given the script will load the daily report for **yesterday**!

*Caution:*
You cannot load a daily report for the current day, in fact you even have to wait half a day or longer (at least in Europe I'll have to wait until 18:00 to get the report for yesterday).

If the download succeeds, it will decompress the downloaded file, import its content into the database and finally remove the file.

## Test your setup

Run <tt>update.sh</tt> and you should see the message from the Autoingestion class (hopefully something like "File Downloaded Successfully"). You should now test wether the <tt>sales</tt> table contains the entries from this import, looking for entries with the same BeginDate date like the script date (assuming that you had downloads for your APP at this date).

*Hint:*
For debugging purposes the script logs error or success messages to a logfile under <tt>~/Library/Logs/update.log</tt> - open the Console app and you should see the entries there.

## Import old reports

Running <tt>update.sh</tt> with older dates will import those reports from Apple.

*Caution:*
You can only go back as much as 30 days but not longer!

## Regular report updates

On unix, you can add a crontab entry to call this <tt>update.sh</tt> script regularly. Open *Cronnix* and create a new entry, specifying the complete path to this script and a time when this script should be called.

Example for a script, running at 18:00 every day:

	0	18	*	*	*	/FOLDER-OF-SCRIPT/update.sh

# 2. Step: Generate a Status Board compatible report

Once importing the data went fine, you can generate graphs for Status Board with the <tt>index.php</tt> script: create a folder within reach of your web server, copy <tt>index.php</tt> and <tt>db.php</tt> there, open the <tt>db.php</tt> script and adjust your MySQL login credentials (this DB class is an old wrapper of mine aging years ago, it can easily be replaced by any other DB wrapper).

The <tt>index.php</tt> script currently looks for download numbers or In-App-Purchases only, generates those numbers for the last 30 days and groups them accordingly. It then outputs those numbers in the JSON format described in the [manual](http://www.panic.com/statusboard/docs/graph_tutorial.pdf).

## Generate graphs

Open Status Board, switch to the setup mode with the gear icon in the upper left corner, then add a Graph to your panel and enter the URL from your server into the Data URL field.

IAP graph example:

	http://your-server.com/path-to-folder/index.php?iap

Download graph example:

	http://your-server.com/path-to-folder/index.php?dl

Because download numbers are default, you can shorten the link like this:

	http://your-server.com/path-to-folder/

# 3. (Optional) PHP web server based graphs

In the `php-graphs` directory you will find some sample PHP scripts
that generate the sales and IAP graphs as a web page, great for when you want to
look at your graphs from outside of Status Board.  Simply install these
files onto a web server with PHP enabled, and install the 
[JpGraph](http://jpgraph.net/) library.  Edit `graph.php` and
set `base_url` to the URL to where you have installed the BOMAAB
php script.  Also change the `require_once` directives to point to
where you installed the JpGraph library.

# Alternate implementation using remote data fetcher

For some reason, Apple's Autoingestion server sometimes returns empty results,
as documented in [this Stack Overflow question](http://stackoverflow.com/questions/17974964/itunes-connect-autoingestion-class-doing-nothing).
This does not always happen, nor does it happen to everyone, and sometimes
(as it happened with me) BOMAAB can be running just fine for a long time
and then suddenly stop working.  In my case I have had BOMAAB running just
fine on my dedicated server, when all of a sudden it stopped working and
now only returns empty results; however BOMAAB runs just fine on a machine
on my home network.

For these situations I have cobbled together an alternate means of
acquiring the iTC data: using a remote host over ssh.  Use the
`update_alternate.sh` script for this.  You will need to set the
`SSH_USER` and `SSH_HOST` variables in the script, as well as create
a password-less ssh key for that remote host. Copy the
Autoingestion.class script file and Autoingestion.properties file to
the remote host.

# Daily sales e-mails

I use [Wevito's automated daily iTunes sales e-mail service](https://wevito.com/)
and love it.  This is a great service that sends a daily email showing the
previous day's sales and IAPs.  Unfortunately it is plagued with issues and
I often do not get reports for days.  Now it looks like it may be gone for
good (haven't received an update since 9/16/2013).  So at the risk of turning
BOMAAB into a "kitchen sink syndrome" project, I have decided to implement my
own daily app email reporting service.  To that end, I have written a Python
script to generate daily iTunes Connect sales e-mails.  This script, located
in the `email-reports` directory is named `report.py.`  It's very rough around
the edges and definitely needs a lot more work but it works well enough that
I decided to include it.  You'll need to sign up for an account with the
[Currency API](http://currency-api.appspot.com) (it's free).  They will
give you an API key which you will need to add to the python script.
You'll also need to edit the script to put in the e-mail
address you'd like your reports sent to, as well as your iTunes Connect
database name, username and password.  Then just run the script from `cron.`
Be sure and run it sufficiently long after BOMAAB's update script to ensure
that the sales data has been downloaded.  Or, you can set `EMAIL_DAILY_REPORTS`
to `YES` in `update.sh` and it will automatically run the e-mail report script
after it has downloaded the latest data.

Things that still need to be done:

* <del>Not sure if this script handles in-app purchases or not. I think they are
  included as part of the general sales data.  Might be nice to separate them
  out into a separate In-app Purchases section.</del>
* <del>The script does not differentiate between new app purchases and upgrades.
  Upgrades are included in the number of units for each app.  However, since
  upgrades are free, this doesn't affect the proceeds shown.  There is a
  version number field in the iTunes data, so it is possible to separate out
  upgrades; I just didn't feel like doing it. :-P</del>
* I've added support for separating out app sales, IAPs, and updates.
  However this is pretty hacky (even more so than the rest of the script)
  and is definitely untested.  Also there is no support for Newsstand
  subscriptions; they appear as generic In-App Purchases.
* Lots of error checking, prettification and etc.

# Notes

- you can add htaccess/htpasswd or any other security measures to your graph script folder
- again for improved security you can seperate the <tt>update.sh</tt> script folder from your graph script folder
- apart from my university days long ago this is my first bash script - it's fairly tested but a unix geek could improve it, I bet
- direct purchase numbers are not handled - yet
- you can copy and modify the <tt>update.sh</tt> script to import even older daily reports you might have in a backup

# Links

- the MySQL structure and import idea based on [Björn Sållarp AppDailySales Import](http://blog.sallarp.com/fetching-app-store-sales-statistics-from-itunes-connect-into-mysql-using-appdailysales/) although I prefer Apples download Java class
- Apples [APP Store Reporting Instructions](http://www.apple.com/itunesnews/docs/AppStoreReportingInstructions.pdf) for explanation of CSV fields

## Contact

[Oliver Michalak](mailto:oliver@werk01.de) - [omichde](https://twitter.com/omichde)

## License

BOMAAB is available under the MIT license:

	Permission is hereby granted, free of charge, to any person obtaining a copy
	of this software and associated documentation files (the "Software"), to deal
	in the Software without restriction, including without limitation the rights
	to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
	copies of the Software, and to permit persons to whom the Software is
	furnished to do so, subject to the following conditions:

	The above copyright notice and this permission notice shall be included in
	all copies or substantial portions of the Software.

	THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
	IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
	FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
	AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
	LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
	OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
	THE SOFTWARE.

