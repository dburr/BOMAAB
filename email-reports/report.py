#!/usr/bin/python

import sys
import socket
import json
import urllib2
import MySQLdb as mdb
import smtplib
import socket
import pycountry
import operator
import os.path
from calendar import monthrange
from collections import OrderedDict
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date, timedelta

# import options
# this is probably not the best way to do it, but oh well
sys.dont_write_bytecode = True
from options import *

# initialize database
dbcon = mdb.connect(db_host, db_user, db_password, db_name);

# exchange rates hash populated on demand
exchange_rates = {}

# warning messages
warnings = []

sales_data = {}
iap_data = {}
update_data = {}

sales_by_country = {}
iaps_by_country = {}
updates_by_country = {}

# some currencies are currently unsupported by the Currency API,
# so we pre-define their exchange rates here
# NOTE: now loading from file
#unsupported_currencies = {}
#unsupported_currencies = {"CNY": 0.17, "NOK": 0.16}
unsupported_currencies = {}
unsup_file_path = os.path.abspath(os.path.dirname(sys.argv[0])) + os.path.sep + 'unsupported_currency_rates.json'
print unsup_file_path
if os.path.isfile(unsup_file_path):
  try:
    unsupported_currency_json_data=open(unsup_file_path)
    unsupported_currencies = json.load(unsupported_currency_json_data)
    print unsupported_currencies
  except IOError:
    print 'Error: could not read unsupported_currency_rates.json, starting with empty data set'
else:
  print "Warning: could not find unsupported_currency_rates.json, starting with empty data set"

def get_exchange_rate(country_code):
  global warnings
  if country_code == "USD":
    exchange_rate = 1.0
  elif country_code in unsupported_currencies:
    print "WARNING: using predefined exchange rate of %f for %s" % (unsupported_currencies[country_code], country_code)
    warnings.append("using predefined exchange rate of %f for %s" % (unsupported_currencies[country_code], country_code))
    exchange_rate = unsupported_currencies[country_code]
  else:
    if country_code in exchange_rates:
      exchange_rate = exchange_rates[country_code]
    else:
      json_data = json.load(urllib2.urlopen("http://currency-api.appspot.com/api/" + country_code + "/USD.json?key=" + api_key))
      print json_data
      if "success" in json_data:
        success = json_data["success"]
        if success:
          print "SUCCESS"
          exchange_rate = json_data["rate"]
          print "rate = %f" % exchange_rate
          exchange_rates[country_code] = exchange_rate
        else:
          print "FAIL"
          print "WARNING: could not get exchange rate for " + country_code + " (possibly unsupported by API), assuming 1.0"
          warnings.append("could not get exchange rate for " + country_code + " (possibly unsupported by API), asuming 1.0")
          exchange_rate = 1
      else:
          print "WARNING: could not get exchange rate for " + country_code + " (possibly unsupported by API), assuming 1.0"
          warnings.append("could not get exchange rate for " + country_code + " (possibly unsupported by API), asuming 1.0")
          exchange_rate = 1
  print "returning %f" % exchange_rate
  return exchange_rate

#def get_exchange_rates():
#  global exchange_rates
#  # get country codes
#  ccodes = get_country_codes()
#  for code in ccodes:
#    exchange_rates[code] = get_exchange_rate(code)

#def get_country_codes():
#  data = urllib2.urlopen('http://download.geonames.org/export/dump/countryInfo.txt')
#  ccodes = []
#  for line in data.read().split('\n'):
#    if not line.startswith('#'):
#      line = line.split('\t')
#      try:
#        if line[10]:
#          ccodes.append(line[10])
#      except IndexError:
#        pass
#  ccodes = list(set(ccodes))
#  ccodes.sort()
#  return ccodes

#def get_exchange_rate(country_code):
#  json_data = json.load(urllib2.urlopen("http://rate-exchange.appspot.com/currency?from=" + country_code + "&to=USD"))
#  if "rate" in json_data:
#    rate = json_data["rate"]
#  else:
#    rate = 1
#  return rate

time_delta = 1
do_monthly = False
start_date = ""
end_date = ""
month_year = ""

if len(sys.argv) == 2:
  if sys.argv[1] == "monthly":
    do_monthly = True
    # assume this is being run on the 1st of the new month
    # so we need to find the last month and calc # of days
    today = date.today()
    first = date(day=1, month=today.month, year=today.year)
    lastMonthEnd = first - timedelta(days=1)
    lastMonthStart = date(day=1, month=lastMonthEnd.month, year=lastMonthEnd.year)
    start_date = lastMonthStart.strftime('%Y-%m-%d')
    end_date = lastMonthEnd.strftime('%Y-%m-%d')
    month_year = lastMonthStart.strftime('%Y-%m')
    print start_date
    print end_date
    #date_range = monthrange(2011, 2)

    #print date_range
    # print lastMonth.strftime("%Y%m")
  else:
    time_delta = int(sys.argv[1])

if do_monthly:
  query = "SELECT DISTINCT SKU FROM sales WHERE BeginDate = '" + start_date + "' AND EndDate = '" + end_date + "' ORDER BY 'SKU' ASC";
else:
  yesterday = date.today() - timedelta(time_delta)
  yesterday_as_string = yesterday.strftime('%Y-%m-%d')
  print yesterday_as_string
  query = "SELECT DISTINCT SKU FROM sales WHERE BeginDate = '" + yesterday_as_string + "' AND EndDate = '" + yesterday_as_string + "' ORDER BY 'SKU' ASC";

#get_exchange_rates()

# get skus
cur = dbcon.cursor()
#cur.execute("SELECT * FROM sales WHERE BeginDate = '" + yesterday_as_string + "' AND EndDate = '" + yesterday_as_string + "' ORDER BY 'SKU' ASC, 'CountryCode' ASC");
cur.execute(query);
rows = cur.fetchall()
if cur.rowcount == 0:
  print "Error: no data"
else:
  skus = []
  for sku in rows:
    skus.append(sku[0])

  for sku in skus:
    # now get countries where that sku was sold
    cur = dbcon.cursor()
    cur.execute("SELECT DISTINCT CountryCode FROM sales WHERE SKU = '" + sku + "' AND BeginDate = '" + yesterday_as_string + "' AND EndDate = '" + yesterday_as_string + "' ORDER BY 'CountryCode' ASC");
    rows = cur.fetchall()
    if cur.rowcount == 0:
      print "Error: no data"
    else:
      countries = []
      for country in rows:
        countries.append(country[0])

      for country in countries:
        # now get sales data for that country
        cur = dbcon.cursor()
        cur.execute("SELECT Title, Version, Units, DeveloperProceeds, CustomerCurrency, CurrencyOfProceeds, ProductTypeIdentifier, AppleIdentifier, ParentIdentifier FROM sales WHERE SKU = '" + sku + "' AND CountryCode = '" + country + "' AND BeginDate = '" + yesterday_as_string + "' AND EndDate = '" + yesterday_as_string + "' ORDER BY 'SKU' ASC, 'CountryCode' ASC");
        rows = cur.fetchall()
        if cur.rowcount == 0:
          print "Error: no data"
        else:
          print "Sales of " + sku + " in " + country + ":"
          for item in rows:
            title = item[0]
            version = item[1]
            units = item[2]
            developer_proceeds = item[3]
            customer_currency = item[4]
            currency_of_proceeds = item[5]
            product_type_identifier = item[6]
            apple_identifier = item[7]
            parent_identifier = item[8]
            print "version: %s units: %d proceeds: %.2f currency: %s (%s)  type: %s  apple_id: %s  parent_id: %s" % (version, units, developer_proceeds, customer_currency, currency_of_proceeds, product_type_identifier, apple_identifier, parent_identifier)
            datum = {}
            # Free or paid apps
            if product_type_identifier == "1" \
            or product_type_identifier == "1F" \
            or product_type_identifier == "1T" \
            or product_type_identifier == "F1":
              print "APP SALE"
              if country in sales_by_country:
                sales_by_country[country] += units
              else:
                sales_by_country[country] = units
              if sku in sales_data:
                datum = sales_data[sku]
              if "units" in datum:
                units += datum["units"]
              exchange_rate = get_exchange_rate(currency_of_proceeds)
              sales_in_dollars = (developer_proceeds * exchange_rate) * units
              if "proceeds" in datum:
                sales_in_dollars += datum["proceeds"]
              datum["title"] = title
              datum["id"] = apple_identifier
              datum["units"] = units
              datum["proceeds"] = sales_in_dollars
              sales_data[sku] = datum
              print datum
            # IAPs
            # currently treating subscriptions as IAPs, should separate later?
            elif product_type_identifier == "IA1" \
            or product_type_identifier == "IA9" \
            or product_type_identifier == "IAY" \
            or product_type_identifier == "IAC" \
            or product_type_identifier == "FI1":
              print "IAP"
              if country in iaps_by_country:
                iaps_by_country[country] += units
              else:
                iaps_by_country[country] = units
              if sku in iap_data:
                datum = iap_data[sku]
              if "units" in datum:
                units += datum["units"]
              exchange_rate = get_exchange_rate(currency_of_proceeds)
              sales_in_dollars = (developer_proceeds * exchange_rate) * units
              if "proceeds" in datum:
                sales_in_dollars += datum["proceeds"]
              datum["title"] = title
              datum["id"] = apple_identifier
              datum["units"] = units
              datum["proceeds"] = sales_in_dollars
              iap_data[sku] = datum
              print datum
            # updates
            elif product_type_identifier == "7" \
            or product_type_identifier == "7F" \
            or product_type_identifier == "7T" \
            or product_type_identifier == "F7":
              print "UPDATE"
              if country in updates_by_country:
                updates_by_country[country] += units
              else:
                updates_by_country[country] = units
              if sku in update_data:
                datum = update_data[sku]
              if "units" in datum:
                units += datum["units"]
              # updates only track units
              datum["title"] = title
              datum["id"] = apple_identifier
              datum["units"] = units
              update_data[sku] = datum
              print datum

  # keep running total
  todays_take = 0.0

  # got all data, time to create message
  message = MIMEMultipart('alternative')
  message['From'] = from_address
  message['To'] = to_address
  if do_monthly:
    message['Subject'] = "Monthly App Sales for " + month_year
  else:
    message['Subject'] = "Daily App Sales for " + yesterday_as_string
  message_text = "Please view this message in a HTML capable email client."
  message_html = "<HTML><head><style>"
  # include css here if needed
  message_html += "</style></head><body>"

  # should almost always have sales data, but better safe than sorry
  if sales_data:
    print "SUMMARY OF SALES DATA:"
    sorted_sales_data = OrderedDict(sorted(sales_data.iteritems(), key=lambda x: x[1]['units'], reverse=True))
    for sku in sorted_sales_data:
      datum = sorted_sales_data[sku]
      print "Title: %s  Units sold: %s  Proceeds in USD: $%.2f" % (datum["title"], datum["units"], datum["proceeds"])

    message_html += "<p><H3>Daily App Sales for " + yesterday_as_string + "</H3>"
    message_html += "<TABLE><TR><TH style=\"background-color: #000000; color: #FFFFFF; text-align: left\">SKU</TH><TH style=\"background-color: #000000; color: #FFFFFF; text-align: left\">App Title</TH><TH style=\"background-color: #000000; color: #FFFFFF; text-align: right\">Units</TH><TH style=\"background-color: #000000; color: #FFFFFF; text-align: right\">Proceeds</TH></TR>"
    # 99FFFF blue
    # C8C8C8 gray
    line_no = 1
    total_proceeds = 0.0
    total_units_sold = 0
    for sku in sorted_sales_data:
      line_color = "#C8C8C8" 
      if line_no % 2 == 0:
        line_color = "#99FFFF"
      datum = sorted_sales_data[sku]
      the_link = "https://itunes.apple.com/us/app/id" + datum["id"]
      if include_links:
        message_html += "<TR style=\"background-color: %s\"><TD ALIGN=left><A HREF=\"%s\">%s</A></TD>" % (line_color, the_link, sku)
        message_html += "<TD ALIGN=left><A HREF=\"%s\">%s</A></TD>" % (the_link, datum["title"])
      else:
        message_html += "<TR style=\"background-color: %s\"><TD ALIGN=left>%s</TD>" % (line_color, sku)
        message_html += "<TD ALIGN=left>%s</TD>" % datum["title"]
      # https://itunes.apple.com/us/app/id425068705
      message_html += "<TD ALIGN=right>%ld</TD>" % datum["units"]
      message_html += "<TD ALIGN=right>$%.2f</TD></TR>" % datum["proceeds"]
      line_no += 1
      total_proceeds += datum["proceeds"]
      total_units_sold += datum["units"]
      todays_take += datum["proceeds"]

    message_html += '<TFOOT style="background-color: #000000; color: #FFFFFF">'
    message_html += '<TD></TD>'
    message_html += '<TD ALIGN=right>TOTAL</TD>'
    message_html += '<TD ALIGN=right>%ld</TD>' % total_units_sold
    message_html += '<TD ALIGN=right>$%.2f</TD>' % total_proceeds

    message_html += "</TFOOT></TABLE></p>"

    if sales_by_country:
      message_html += "<p><H3>Sales By Country:</H3>"
      message_html += "<TABLE><TR><TH style=\"background-color: #000000; color: #FFFFFF; text-align: left\">Country</TH><TH style=\"background-color: #000000; color: #FFFFFF; text-align: left\">Units</TH></TR>"
      # 99FFFF blue
      # C8C8C8 gray
      line_no = 1
      total_units_sold = 0
      sorted_sales_by_country = sorted(sales_by_country.iteritems(), key=operator.itemgetter(1), reverse=True)
      print sorted_sales_by_country
      for datum in sorted_sales_by_country:
        country = datum[0]
        nunits = datum[1]
        the_country = pycountry.countries.get(alpha2=country)
        line_color = "#C8C8C8" 
        if line_no % 2 == 0:
          line_color = "#99FFFF"
        #nunits = sales_by_country[country]
        message_html += "<TR style=\"background-color: %s\"><TD ALIGN=left>%s</TD>" % (line_color, the_country.name)
        message_html += "<TD ALIGN=left>%ld</TD></TR>" % nunits
        line_no += 1
        total_units_sold += nunits

      message_html += '<TFOOT style="background-color: #000000; color: #FFFFFF">'
      message_html += '<TD ALIGN=right>TOTAL</TD>'
      message_html += '<TD ALIGN=right>%ld</TD>' % total_units_sold
      message_html += "</TFOOT></TABLE></p>"

  if iap_data:
    print "SUMMARY OF IAP DATA:"
    sorted_iap_data = OrderedDict(sorted(iap_data.iteritems(), key=lambda x: x[1]['units'], reverse=True))
    for sku in sorted_iap_data:
      datum = sorted_iap_data[sku]
      print "Title: %s  Units sold: %s  Proceeds in USD: $%.2f" % (datum["title"], datum["units"], datum["proceeds"])

    # include css here if needed
    message_html += "<y><H3>In-App Purchases for " + yesterday_as_string + "</H3>"
    message_html += "<TABLE><TR><TH style=\"background-color: #000000; color: #FFFFFF; text-align: left\">SKU</TH><TH style=\"background-color: #000000; color: #FFFFFF; text-align: left\">Title</TH><TH style=\"background-color: #000000; color: #FFFFFF; text-align: right\">Units</TH><TH style=\"background-color: #000000; color: #FFFFFF; text-align: right\">Proceeds</TH></TR>"
    # 99FFFF blue
    # C8C8C8 gray
    line_no = 1
    total_proceeds = 0.0
    total_units_sold = 0
    for sku in sorted_iap_data:
      line_color = "#C8C8C8" 
      if line_no % 2 == 0:
        line_color = "#99FFFF"
      datum = sorted_iap_data[sku]
      message_html += "<TR style=\"background-color: %s\"><TD ALIGN=left>%s</TD>" % (line_color, sku)
      message_html += "<TD ALIGN=left>%s</TD>" % datum["title"]
      # https://itunes.apple.com/us/app/id425068705
      message_html += "<TD ALIGN=right>%ld</TD>" % datum["units"]
      message_html += "<TD ALIGN=right>$%.2f</TD></TR>" % datum["proceeds"]
      line_no += 1
      total_proceeds += datum["proceeds"]
      todays_take += datum["proceeds"]
      total_units_sold += datum["units"]

    message_html += '<TFOOT style="background-color: #000000; color: #FFFFFF">'
    message_html += '<TD></TD>'
    message_html += '<TD ALIGN=right>TOTAL</TD>'
    message_html += '<TD ALIGN=right>%ld</TD>' % total_units_sold
    message_html += '<TD ALIGN=right>$%.2f</TD>' % total_proceeds

    message_html += "</TFOOT></TABLE></p>"

    if iaps_by_country:
      message_html += "<p><H3>In-App Purchases By Country:</H3>"
      message_html += "<TABLE><TR><TH style=\"background-color: #000000; color: #FFFFFF; text-align: left\">Country</TH><TH style=\"background-color: #000000; color: #FFFFFF; text-align: left\">Units</TH></TR>"
      # 99FFFF blue
      # C8C8C8 gray
      line_no = 1
      total_units_sold = 0
      sorted_iaps_by_country = sorted(iaps_by_country.iteritems(), key=operator.itemgetter(1), reverse=True)
      for datum in sorted_iaps_by_country:
        country = datum[0]
        nunits = datum[1]
        the_country = pycountry.countries.get(alpha2=country)
        line_color = "#C8C8C8" 
        if line_no % 2 == 0:
          line_color = "#99FFFF"
        nunits = iaps_by_country[country]
        message_html += "<TR style=\"background-color: %s\"><TD ALIGN=left>%s</TD>" % (line_color, the_country.name)
        message_html += "<TD ALIGN=left>%ld</TD></TR>" % nunits
        line_no += 1
        total_units_sold += nunits

      message_html += '<TFOOT style="background-color: #000000; color: #FFFFFF">'
      message_html += '<TD ALIGN=right>TOTAL</TD>'
      message_html += '<TD ALIGN=right>%ld</TD>' % total_units_sold
      message_html += "</TFOOT></TABLE></p>"

  if update_data:
    print "SUMMARY OF UPDATE DATA:"
    sorted_update_data = OrderedDict(sorted(update_data.iteritems(), key=lambda x: x[1]['units'], reverse=True))
    for sku in sorted_update_data:
      datum = sorted_update_data[sku]
      print "Title: %s  Units downloaded: %s" % (datum["title"], datum["units"])

    # include css here if needed
    message_html += "<y><H3>App Updates for " + yesterday_as_string + "</H3>"
    message_html += "<TABLE><TR><TH style=\"background-color: #000000; color: #FFFFFF; text-align: left\">SKU</TH><TH style=\"background-color: #000000; color: #FFFFFF; text-align: left\">App Title</TH><TH style=\"background-color: #000000; color: #FFFFFF; text-align: right\">Units</TH></TR>"
    # 99FFFF blue
    # C8C8C8 gray
    line_no = 1
    total_units_sold = 0
    for sku in sorted_update_data:
      line_color = "#C8C8C8" 
      if line_no % 2 == 0:
        line_color = "#99FFFF"
      datum = sorted_update_data[sku]
      the_link = "https://itunes.apple.com/us/app/id" + datum["id"]
      if include_links:
        message_html += "<TR style=\"background-color: %s\"><TD ALIGN=left><A HREF=\"%s\">%s</A></TD>" % (line_color, the_link, sku)
        message_html += "<TD ALIGN=left><A HREF=\"%s\">%s</A></TD>" % (the_link, datum["title"])
      else:
        message_html += "<TR style=\"background-color: %s\"><TD ALIGN=left>%s</TD>" % (line_color, sku)
        message_html += "<TD ALIGN=left>%s</TD>" % datum["title"]
      # https://itunes.apple.com/us/app/id425068705
      message_html += "<TD ALIGN=right>%ld</TD>" % datum["units"]
      line_no += 1
      total_units_sold += datum["units"]

    message_html += '<TFOOT style="background-color: #000000; color: #FFFFFF">'
    message_html += '<TD></TD>'
    message_html += '<TD ALIGN=right>TOTAL</TD>'
    message_html += '<TD ALIGN=right>%ld</TD>' % total_units_sold

    message_html += "</TFOOT></TABLE></p>"

    if updates_by_country:
      message_html += "<p><H3>Updates By Country:</H3>"
      message_html += "<TABLE><TR><TH style=\"background-color: #000000; color: #FFFFFF; text-align: left\">Country</TH><TH style=\"background-color: #000000; color: #FFFFFF; text-align: left\">Units</TH></TR>"
      # 99FFFF blue
      # C8C8C8 gray
      line_no = 1
      total_units_sold = 0
      sorted_updates_by_country = sorted(updates_by_country.iteritems(), key=operator.itemgetter(1), reverse=True)
      for datum in sorted_updates_by_country:
        country = datum[0]
        nunits = datum[1]
        the_country = pycountry.countries.get(alpha2=country)
        line_color = "#C8C8C8" 
        if line_no % 2 == 0:
          line_color = "#99FFFF"
        nunits = updates_by_country[country]
        message_html += "<TR style=\"background-color: %s\"><TD ALIGN=left>%s</TD>" % (line_color, the_country.name)
        message_html += "<TD ALIGN=left>%ld</TD></TR>" % nunits
        line_no += 1
        total_units_sold += nunits

      message_html += '<TFOOT style="background-color: #000000; color: #FFFFFF">'
      message_html += '<TD ALIGN=right>TOTAL</TD>'
      message_html += '<TD ALIGN=right>%ld</TD>' % total_units_sold
      message_html += "</TFOOT></TABLE></p>"




    
  message_html += "<p><h3>Today's Take: $%.2f</h3></p>" % todays_take

  if warnings:
    message_html += "<p><b>Warnings:</b><ol>"
    for warning in warnings:
      message_html += "<li>" + warning + "</li>"
    message_html += "</ol></p>"

  part1 = MIMEText(message_text, 'plain')
  part2 = MIMEText(message_html, 'html')

  message.attach(part1)
  message.attach(part2)

  try:
    smtpObj = smtplib.SMTP('localhost')
    smtpObj.sendmail(from_address, [to_address], message.as_string())
    print "Successfully sent email"
  except SMTPException:
    print "Error: unable to send email"
