#!/bin/bash
#
# enter your credentials here:
# Apple login and password are now set in Autoingestion.properties.
APPLEVENDORID="your-vendor-id"
MYSQLUSER="your-mysql-username"
MYSQLPASSWORD="your-mysql-password"
#
# set this to a directory where you want the update.log placed
LOGDIR="$HOME/Library/Logs"
#
# set to YES if you have OS X-style `date' command (supports `-v' flag)
OSXDATE="NO"
#
# set to YES if your mysql command requires the `--local-infile' flag
# (usually true for Linux/*BSD;  you'll know this if you get the error
# `The used command is not allowed with this MySQL version'
# NOTE: you must also enable this in your mysql server config;
# edit the file /etc/my.cnf, and in the [mysqld] section, add
#      local-infile=1
# then restart mysqld
#      /etc/init.d/mysqld restart
USE_LOCAL_INFILE="YES"
#
# Set to YES to e-mail a copy of app activity.  Be sure and edit the
# email script to set your e-mail address, etc.
EMAIL_DAILY_REPORTS="YES"
#
# Set to the username and host of the machine that runs Autoingestion.class
SSH_HOST=host.example.com
SSH_USER=username
#
# Sometimes ITC update availability is delayed, with the result being that
# at the time this script is run by cron, the updates for that day are not
# yet available.  Enable this option to periodically retry downloading the
# day's updates until they are available.  This requires that you set up
# `atrun' command.  For OS X systems, run the following command:
#    sudo launchctl load -w /System/Library/LaunchDaemons/com.apple.atrun.plist
# For other systems (e.g. Linux) see the `at' man page.
RETRY_DAILY_DOWNLOADS_IF_UNAVAILABLE=YES
#
# assumes Autoingestion.java is in the same directory as this script;
# if different, change this
AUTOINGESTION_LOCATION="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# ensure that mysql is in this PATH
export PATH=/bin:/usr/bin:/usr/local/bin

# get full path to this script
#pushd . > /dev/null
#SCRIPT_PATH="${BASH_SOURCE[0]}";
#while([ -h "${SCRIPT_PATH}" ]) do 
#  cd "`dirname "${SCRIPT_PATH}"`"
#  SCRIPT_PATH="$(readlink "`basename "${SCRIPT_PATH}"`")"; 
#done
#cd "`dirname "${SCRIPT_PATH}"`" > /dev/null
#SCRIPT_PATH="`pwd`";
#popd  > /dev/null
#echo "srcipt=[${SCRIPT_PATH}]"
#echo "pwd   =[`pwd`]"

# get the full path to this script in case we need to re-run ourselves
SCRIPT_NAME="$(cd $(dirname $0); pwd)/$(basename $0)"

cd $(dirname $0)
if [[ -n $1 ]]; then         
	DATE="$1"
else
	if [ "$OSXDATE" = "YES" ]; then
		DATE=$(date -v -1d +%Y%m%d)
	else
		# thanks to:
		# http://www.masaokitamura.com/2009/02/17/how-to-get-yesterdays-date-using-bash-shell-scripting/
		DATE=$(date -d "1 day ago" +%Y%m%d)
	fi
fi
#cd "$AUTOINGESTION_LOCATION" && java Autoingestion $APPLELOGIN $APPLEPASSWORD $APPLEVENDORID Sales Daily Summary $DATE
#pwd
ssh $SSH_USER@$SSH_HOST java Autoingestion Autoingestion.properties 85237526 Sales Daily Summary $DATE
#java Autoingestion Autoingestion.properties 85237526 Sales Daily Summary $DATE
FNAME="S_D_${APPLEVENDORID}_${DATE}.txt"
#if [ -f "$FNAME.gz" ]; then
if ssh -q $SSH_USER@$SSH_HOST test -e ${FNAME}.gz; then
  scp -q $SSH_USER@$SSH_HOST:${FNAME}.gz . && ssh $SSH_USER@$SSH_HOST rm -f ${FNAME}.gz
  rm -f "$FNAME"
	gunzip "$FNAME.gz"
	mysql --user=$MYSQLUSER --password=$MYSQLPASSWORD --database=itunesconnect -e "delete from sales where BeginDate='$DATE' and EndDate='$DATE'"
	if [ "$USE_LOCAL_INFILE" = "YES" ]; then
		mysql --user=$MYSQLUSER --password=$MYSQLPASSWORD --database=itunesconnect --local-infile=1 -e "load data local infile '$FNAME' into table sales fields terminated by '\t' lines terminated by '\n' ignore 1 lines (Provider,ProviderCountry,SKU,Developer,Title,Version,ProductTypeIdentifier,Units,DeveloperProceeds,@BeginDate,@EndDate,CustomerCurrency,CountryCode,CurrencyOfProceeds,AppleIdentifier,CustomerPrice,PromoCode,ParentIdentifier,Subscription,Period) SET BeginDate=str_to_date(@BeginDate, '%m/%d/%Y'), EndDate=str_to_date(@EndDate, '%m/%d/%Y')"
	else
		mysql --user=$MYSQLUSER --password=$MYSQLPASSWORD --database=itunesconnect -e "load data local infile '$FNAME' into table sales fields terminated by '\t' lines terminated by '\n' ignore 1 lines (Provider,ProviderCountry,SKU,Developer,Title,Version,ProductTypeIdentifier,Units,DeveloperProceeds,@BeginDate,@EndDate,CustomerCurrency,CountryCode,CurrencyOfProceeds,AppleIdentifier,CustomerPrice,PromoCode,ParentIdentifier,Subscription,Period) SET BeginDate=str_to_date(@BeginDate, '%m/%d/%Y'), EndDate=str_to_date(@EndDate, '%m/%d/%Y')"
	fi
	rm $FNAME
	echo "$(date "+%Y-%m-%d %H:%M:%S"): $DATE imported" >> "$LOGDIR/update.log"
  if [ "$EMAIL_DAILY_REPORTS" = "YES" ]; then
    python $AUTOINGESTION_LOCATION/email-reports/report.py >/dev/null
  fi
else
	echo "$(date "+%Y-%m-%d %H:%M:%S"): no file $FNAME.gz" >> "$LOGDIR/update.log"
  # no $1 means this script was run from cron, which means that today's
  # ITC update was probably not yet available when the script was run
  if [[ -z $1 -a "$RETRY_DAILY_DOWNLOADS_IF_UNAVAILABLE" = "YES" ]]; then
    echo "ITC stats are probably not yet available for today.  This script will keep"
    echo "trying until they are successfully downloaded.  Check the log file for"
    echo "details and to confirm the successful download."
    at now + 1 hour << _EOF_
"$SCRIPT_NAME"
_EOF_
  fi
fi
