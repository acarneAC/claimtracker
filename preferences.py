# Copyright (c) 2016 Jack Morton <jhm@jemscout.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import pygtk
pygtk.require("2.0")
import gtk
import os
import ConfigParser
import logging

class Preferences(ConfigParser.RawConfigParser):
	def __init__(self):
		ConfigParser.RawConfigParser.__init__(self)

	def load(self, filename):
		self.filename = filename
		# Load global preferences
		if os.access(self.filename, os.W_OK): # Read file if it exists
			self.read(self.filename)

	def save(self):
		try:
			f = open(self.filename, "w")
			self.write(f)
		except (OSError, IOError) as e:
			logging.error("Failed to write global perferences to file " + self.filename)
			logging.error(e)

	def validate(self):
		""" Validates the global preferences """
		# Validate logging parameters
		if not self.has_section("Logging"):
			self.add_section("Logging")
		if not self.has_option("Logging", "filename"):
			self.set("Logging", "filename", "claimtracker.log")
		try:
			if not int(self.get("Logging", "level")) in range(1,6):
				self.set("Logging", "level", "1")
		except: # Out of range or self.has_option fails
			self.set("Logging", "level", "1")

		def loglevel(level):
			return {
				"1": logging.DEBUG,
				"2": logging.INFO,
				"3": logging.WARNING,
				"4": logging.ERROR,
				"5": logging.CRITICAL
			}[level]
		try:
			for h in logging.root.handlers[:]: # Remove any existing handlers
				logging.root.removeHandler(h)
			logging.basicConfig(filename=self.get("Logging", "filename"), \
				level=loglevel(str(self.get("Logging", "level"))), \
				format="%(asctime)s %(levelname)-8s %(message)s", mode="w")
		except:
			error_msg = gtk.MessageDialog(None, 0, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, \
				"FATAL: Could not write to log")
			error_msg.format_secondary_text("Make sure %s is writable and try again." \
				% self.get("Logging", "filename"))
			error_msg.run()
			error_msg.destroy()
			exit()

		# Validate the window parameters
		if not self.has_section("Window"):
			self.add_section("Window")
		try:
			if not int(self.get("Window", "min_to_tray")) in range(0,2):
				self.set("Window", "min_to_tray", "0")
		except: # Out of range or self.has_option fails
			self.set("Window", "min_to_tray", "0")
		try:
			if not int(self.get("Window", "width")):
				self.set("Window", "width", "800")
		except: # ValueError or self.has_option fails
			self.set("Window", "width", "800")
		try:
			if not int(self.get("Window", "height")):
				self.set("Window", "height", "600")
		except: # ValueError or self.has_option fails
			self.set("Window", "height", "600")

		# Validate the web browser
		if not self.has_section("Web"):
			self.add_section("Web")
		if not self.has_option("Web", "browser"):
			self.set("Web", "browser", "C:\Program Files (x86)\Internet Explorer\iexplore.exe")

global preferences
preferences = Preferences()
