#!/usr/bin/python

import json
import urllib2
import MySQLdb as mdb
import smtplib
import socket
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date, timedelta

from_address = 'BOMAAB@' + socket.gethostname()
to_address = 'dburr@borg-cube.com'

# initialize database
dbcon = mdb.connect('localhost', 'dburritc', 'mM7PXhjKs4X', 'itunesconnect');

exchange_rates = {}
sales_data = {}

def get_exchange_rate(country_code):
  exchange_rate = 0.0
  if country_code in exchange_rates:
    exchange_rate = exchange_rates[country_code]
  else:
    json_data = json.load(urllib2.urlopen("http://rate-exchange.appspot.com/currency?from=" + country_code + "&to=USD"))
    if "rate" in json_data:
      exchange_rate = json_data["rate"]
      exchange_rates[country_code] = exchange_rate
    else:
      exchange_rate = 0
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

yesterday = date.today() - timedelta(1)
yesterday_as_string = yesterday.strftime('%Y-%m-%d')
print yesterday_as_string

#get_exchange_rates()

# get skus
cur = dbcon.cursor()
#cur.execute("SELECT * FROM sales WHERE BeginDate = '" + yesterday_as_string + "' AND EndDate = '" + yesterday_as_string + "' ORDER BY 'SKU' ASC, 'CountryCode' ASC");
cur.execute("SELECT DISTINCT SKU FROM sales WHERE BeginDate = '" + yesterday_as_string + "' AND EndDate = '" + yesterday_as_string + "' ORDER BY 'SKU' ASC");
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
        cur.execute("SELECT Title, Version, Units, DeveloperProceeds, CustomerCurrency, CurrencyOfProceeds FROM sales WHERE SKU = '" + sku + "' AND CountryCode = '" + country + "' AND BeginDate = '" + yesterday_as_string + "' AND EndDate = '" + yesterday_as_string + "' ORDER BY 'SKU' ASC, 'CountryCode' ASC");
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
            print "version: %s units: %d proceeds: %.2f currency: %s (%s)" % (version, units, developer_proceeds, customer_currency, currency_of_proceeds)
            datum = {}
            if sku in sales_data:
              datum = sales_data[sku]
            if "units" in datum:
              units += datum["units"]
            exchange_rate = get_exchange_rate(currency_of_proceeds)
            sales_in_dollars = developer_proceeds * exchange_rate
            if "proceeds" in datum:
              sales_in_dollars += datum["proceeds"]
            datum["title"] = title
            datum["units"] = units
            datum["proceeds"] = sales_in_dollars
            sales_data[sku] = datum
            print datum

  for sku in sales_data:
    datum = sales_data[sku]
    print "Title: %s  Units sold: %s  Proceeds in USD: $%.2f" % (datum["title"], datum["units"], datum["proceeds"])

  message = MIMEMultipart('alternative')
  message['From'] = from_address
  message['To'] = to_address
  message['Subject'] = "Daily App Sales for " + yesterday_as_string
  message_text = "Please view this message in a HTML capable email client."
  message_html = "<HTML><head><style>"
  # include css here if needed
  message_html += "</style></head><body><H3>Daily App Sales for " + yesterday_as_string + "</H3>"
  message_html += "<TABLE><TR><TH style=\"background-color: #000000; color: #FFFFFF; text-align: left\">SKU</TH><TH style=\"background-color: #000000; color: #FFFFFF; text-align: left\">App Title</TH><TH style=\"background-color: #000000; color: #FFFFFF; text-align: right\">Units</TH><TH style=\"background-color: #000000; color: #FFFFFF; text-align: right\">Proceeds</TH></TR>"
# 99FFFF blue
# C8C8C8 gray
  line_no = 1
  total_proceeds = 0.0
  total_units_sold = 0
  for sku in sales_data:
    line_color = "#C8C8C8" 
    if line_no % 2 == 0:
      line_color = "#99FFFF"
    datum = sales_data[sku]
    message_html += "<TR style=\"background-color: " + line_color + "\"><TD ALIGN=left>" + sku + "</TD>"
    message_html += "<TD ALIGN=left>" + datum["title"] + "</TD>"
    message_html += "<TD ALIGN=right>%ld</TD>" % datum["units"]
    message_html += "<TD ALIGN=right>$%.2f</TD></TR>" % datum["proceeds"]
    line_no += 1
    total_proceeds += datum["proceeds"]
    total_units_sold += datum["units"]

  message_html += '<TFOOT style="background-color: #000000; color: #FFFFFF">'
  message_html += '<TD></TD>'
  message_html += '<TD ALIGN=right>TOTALS</TD>'
  message_html += '<TD ALIGN=right>%ld</TD>' % total_units_sold
  message_html += '<TD ALIGN=right>$%.2f</TD>' % total_proceeds

  message_html += "</TFOOT></TABLE>"

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
