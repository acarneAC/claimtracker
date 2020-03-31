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
import logging
import csv
import tables
from ConfigParser import NoOptionError
from preferences import preferences

class FileDialog(gtk.FileChooserDialog):
	""" Spawn the dialog for selecting a file to open or save """

	def __init__(self, title, none, action, buttons, activate, files):
		super(FileDialog, self).__init__(title, none, action, buttons)
		logging.debug("File->Open File/Save File dialog...")

		# Prepare filters

		# For the 'open' dialog only:
		if files == 0:
			filter_csv = gtk.FileFilter()
			filter_csv.set_name("Comma-delimited CSV (*.csv)")
			filter_csv.add_pattern("*.csv")
			self.add_filter(filter_csv)

		# For all dialogs:
		filter_all = gtk.FileFilter()
		filter_all.set_name("All files (*.*)")
		filter_all.add_pattern("*")
		self.add_filter(filter_all)

		# Activation response
		self.activate = activate

		# Prepare dialog
		self.set_default_response(gtk.RESPONSE_OK)
		self.connect("file-activated", self.activate)
		self.connect("response", self.response)

	def response(self, widget, data=None):
		if data == (-5):
			self.activate(widget, data)
		else:
			self.destroy()

class PreferencesDialog:
	""" Spawn the dialog for adjusting global preferences """
	def __init__(self, widget, data=None):
		logging.debug("Launching PreferencesDialog")
		self.preference_changes = {"log_file": preferences.get("Logging", "filename"), \
			"log_level": preferences.get("Logging", "level"), \
			"min_to_tray": preferences.get("Window", "min_to_tray"), \
			"browser": preferences.get("Web", "browser")}

		# Build the dialog
		self.dialog = gtk.Dialog(title = "Preferences")
		self.dialog.connect("delete-event", self.on_cancel)

		# Logging preferences
		log_label = gtk.Label("Logging:")
		log_label.set_alignment(xalign=0, yalign=0.5)

		log_file = gtk.HBox()
		log_file_label = gtk.Label("Log file: ")
		log_file_input = gtk.Entry(256)
		log_file_input.set_text(preferences.get("Logging", "filename"))
		log_file_input.connect("changed", self.on_log_file, log_file_input)
		log_file.pack_start(log_file_label, False, False, 5)
		log_file.pack_start(log_file_input, True, True, 5)

		log_level = gtk.HBox()
		log_level_label = gtk.Label("Logging level: ")
		log_levels = ["Debug", "Info", "Warning", "Error", "Critical"]
		combobox = gtk.combo_box_new_text()
		for lev in log_levels:
			combobox.append_text(lev)
		combobox.set_active(int(preferences.get("Logging", "level")) - 1)
		combobox.connect("changed", self.on_log_level)
		log_level.pack_start(log_level_label, False, False, 5)
		log_level.pack_start(combobox, True, True, 5)

		# Minimize-to-tray preferences
		min_tray = gtk.HBox()
		min_tray_checkbutton = gtk.CheckButton()
		if int(preferences.get("Window", "min_to_tray")) == 1:
			min_tray_checkbutton.set_active(True)
		min_tray_checkbutton.connect("toggled", self.on_min_tray)
		min_tray_label = gtk.Label("Minimize to tray")
		min_tray_label.set_alignment(xalign=0, yalign=0.5)
		min_tray.pack_start(min_tray_checkbutton, False, False, 5)
		min_tray.pack_start(min_tray_label, True, True, 5)

		# Web browser preferences
		browser = gtk.HBox()
		browser_label = gtk.Label("Web browser: ")
		browser_input = gtk.Entry(256)
		browser_input.set_text(preferences.get("Web", "browser"))
		browser_input.connect("changed", self.on_browser, browser_input)
		browser.pack_start(browser_label, False, False, 5)
		browser.pack_start(browser_input, True, True, 5)

		# Build the bottom frame that holds the apply/cancel buttons
		bottom_frame = gtk.HBox()
		cancel_button = gtk.Button(label="Cancel", stock=gtk.STOCK_CANCEL)
		cancel_button.connect("clicked", self.on_cancel)
		apply_button = gtk.Button(label="Import", stock=gtk.STOCK_APPLY)
		apply_button.connect("clicked", self.on_apply)
		bottom_frame.pack_end(apply_button, False, False, 0)
		bottom_frame.pack_end(cancel_button, False, False, 0)

		# Pack the dialog
		self.dialog.vbox.pack_start(log_label, False, False, 5)
		self.dialog.vbox.pack_start(log_file, False, False, 2)
		self.dialog.vbox.pack_start(log_level, False, False, 2)

		# XXX: minimize to tray is not implemented
		#self.dialog.vbox.pack_start(gtk.HSeparator(), False, False, 5)
		#self.dialog.vbox.pack_start(min_tray, False, False, 2)
		self.dialog.vbox.pack_start(gtk.HSeparator(), False, False, 5)
		self.dialog.vbox.pack_start(browser, False, False, 5)
		self.dialog.vbox.pack_start(bottom_frame, True, True, 0)
		self.dialog.show_all()
		response = self.dialog.run()
		self.dialog.destroy()

	def on_log_file(self, widget, data=None):
		text = data.get_text()
		self.preference_changes["log_file"] = text

	def on_log_level(self, widget, data=None):
		new_level = widget.get_active()
		self.preference_changes["log_level"] = new_level + 1

	# XXX: minimize to tray is not not implemented
	def on_min_tray(self, widget, data=None):
		if widget.get_active() == 1:
			self.preference_changes["min_to_tray"] = "1"
		else:
			self.preference_changes["min_to_tray"] = "0"

	def on_browser(self, widget, data=None):
		text = data.get_text()
		self.preference_changes["browser"] = text

	def on_apply(self, widget, data=None):
		logging.debug("PreferencesDialog: apply changes: %s" % \
			["%s: %s" % (key, self.preference_changes[key]) for key in \
			self.preference_changes.keys()])
		preferences.set("Logging", "filename", self.preference_changes["log_file"])
		preferences.set("Logging", "level", self.preference_changes["log_level"])
		preferences.set("Window", "min_to_tray", self.preference_changes["min_to_tray"])
		preferences.set("Web", "browser", self.preference_changes["browser"])

		preferences.validate()
		self.dialog.response(gtk.RESPONSE_OK)

	def on_cancel(self, widget, data=None):
		logging.debug("PreferencesDialog: cancel")
		self.dialog.response(gtk.RESPONSE_CANCEL)

class ClaimTableWizard:
	""" Spawn the dialog for importing the rows and settings of a table """

	def __init__(self, parent, filename, claimtable=None):
		logging.debug("Launching ClaimTableWizard")

		self.filename = filename
		self.parent = parent
		if not claimtable:
			self.re_import = False
			self.claimtable = self.parent.on_new_table(self, data=self.filename)
			_, fil = os.path.split(self.filename)
			self.claimtable.set_tab_text(fil)
		else:
			self.re_import = True
			self.claimtable = claimtable

		# Build the dialog
		self.dialog = gtk.Dialog(title = "Import as...")
		self.dialog.connect("delete-event", self.on_cancel)

		# Open the file
		try:
			self.f = open(self.filename, "rb")
		except (OSError, IOError) as e:
			logging.error("ClaimTableWizard: unable to open csv file " + self.filename)
			logging.error(e)
			error_msg = gtk.MessageDialog(self.parent.window, 0, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, \
				"Can not open csv file")
			error_msg.format_secondary_text("Make sure %s is readable and try again." \
				% self.filename)
			error_msg.run()
			error_msg.destroy()
			self.claimtable.destroy()
			return

		# Build the treeview model
		self.reader = csv.reader(self.f)
		try:
			self.liststore = gtk.ListStore(str, str)
			headers = self.reader.next()
			for h in headers:
				self.liststore.append([h, "Not imported"])
			treeview = gtk.TreeView(self.liststore)
			treeview.set_grid_lines(gtk.TREE_VIEW_GRID_LINES_BOTH)
		except StopIteration:
			logging.error("ClaimTableWizard: unable to parse file " + self.filename)
			error_msg = gtk.MessageDialog(self.parent.window, 0, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, \
				"Unable to parse file")
			error_msg.format_secondary_text("Please select another file and try again.")
			error_msg.run()
			error_msg.destroy()
			self.claimtable.destroy()
			return

		# Open the file with the options file mapping settings
		if not claimtable and self.claimtable.options.items("Mapping"):
			self.open_w_mapping()
			return
		else:
			self.open_w_mapping()	# Re-import the table

		# Build column one
		cell = gtk.CellRendererText()
		column_one = gtk.TreeViewColumn("Column", cell, text=0)
		treeview.append_column(column_one)

		# Build column two, a combo box to select the appropriate header
		combo = gtk.CellRendererCombo()
		combolist = gtk.ListStore(*[str for t in tables.table_layout["header"]])
		combobox = gtk.ComboBox(combolist)
		combobox.append_text("Not imported")
		for h in tables.table_layout["header"]:
			combobox.append_text(h)
		combo.set_property("editable", True)
		combo.set_property("model", combolist)
		combo.set_property("text-column", 0)
		combo.set_property("has-entry", False)
		combo.connect("edited", self.on_combo_changed)
		column_two = gtk.TreeViewColumn("Import as", combo, text=1)
		treeview.append_column(column_two)

		# Build the province selector radiobuttons
		provinces = list(self.claimtable.claimtable.supported().keys())
		def change_province(button):
			self.claimtable.options.set("Settings", "province", button.get_label())

		province_frame = gtk.HBox()
		label = gtk.Label("Province/State: ")
		button_zero = gtk.RadioButton(label=provinces[0])
		button_zero.connect("pressed", change_province)
		province_frame.pack_end(button_zero, False, False, 0)
		for p in provinces[1:]:
			button = gtk.RadioButton(label=p, group=button_zero)
			if self.claimtable.options.get("Settings", "province") == p:
				button.set_active(True)
			button.connect("pressed", change_province)
			province_frame.pack_end(button, False, False, 0)
		province_frame.pack_end(label, False, False, 0)

		# Build the bottom frame that holds the apply/cancel buttons and the province radiobuttons
		bottom_frame = gtk.HBox()
		cancel_button = gtk.Button(label="Cancel", stock=gtk.STOCK_CANCEL)
		cancel_button.connect("clicked", self.on_cancel)
		apply_button = gtk.Button(label="Import", stock=gtk.STOCK_APPLY)
		apply_button.connect("clicked", self.on_apply)
		bottom_frame.pack_end(apply_button, False, False, 0)
		bottom_frame.pack_end(cancel_button, False, False, 0)
		bottom_frame.pack_end(province_frame, False, False, 20)

		# Pack the dialog
		self.dialog.vbox.pack_start(treeview, True, True, 0)
		self.dialog.vbox.pack_end(bottom_frame, True, True, 0)
		self.dialog.show_all()
		height = treeview.get_cell_area(0, column_one).height
		self.dialog.resize(320, height*len(headers))

		response = self.dialog.run()
		self.dialog.destroy()
		if response == gtk.RESPONSE_CANCEL:	# Hit the 'Cancel' button...
			if not claimtable:
				self.claimtable.destroy()

	def open_w_mapping(self, re_import=False):
		""" Attempt to open the file with the mapping that is set in the options file """
		data = {}
		logging.debug("ClaimTableWizard: attempting open_w_mapping()")

		for key, text in self.claimtable.options.items("Mapping"):
			for path, col in enumerate(self.liststore):
				# RawConfigParser has a bug, which is why it is both hacking and necessary for this
				# comparison to be in lowercase.  Options in ConfigParser are case insensivitve by
				# default, but the type should be changeable, as documented here:
				# http://stackoverflow.com/questions/19359556
				# But (for this version?) the optionxform is cannot be replaced! So we are forced to
				# test for lower case.
				c = self.liststore[path][0].lower()
				if key == c:
					self.on_combo_changed(None, path, text)
		if not self.re_import:
			self.on_apply(None)

	def on_combo_changed(self, widget, path, text):
		self.liststore[path][1] = text

	def on_apply(self, widget):
		data = {}
		we_got_one = False

		if not self.re_import:
			logging.debug("ClaimTableWizard: applying 'import as'...")
		else:
			logging.debug("ClaimTableWizard: re-importing the table...")
			# Clear the table
			for ent in self.claimtable.claimtable:
				self.claimtable.on_delete_nocheck(0)

		for path, col in enumerate(self.liststore):
			self.f.seek(0)
			self.reader.next()
			if self.liststore[path][1] != "Not imported":
				we_got_one = True
				# self.liststore[path][1] is the column title, col is the depth to the column
				data[self.liststore[path][1]] = []
				for row in self.reader:
					data[self.liststore[path][1]].append(row[path])

		# Set mapping in table options
		for path, col in enumerate(self.liststore):
			self.claimtable.options.set("Mapping", self.liststore[path][0], self.liststore[path][1])
		# Validate the mapping
		self.claimtable.validate_options()

		if we_got_one == False:
			logging.error("ClaimTableWizard: no column to import selected!")
			error_msg = gtk.MessageDialog(self.parent.window, 0, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, \
				"No columns selected")
			error_msg.format_secondary_text("Please select at least one column to import and " \
				"try again.")
			error_msg.run()
			error_msg.destroy()
			self.dialog.response(gtk.RESPONSE_CANCEL)
		else:
			self.claimtable.claimtable.load_csv(data)
			logging.debug("ClaimTableWizard: success!")
			self.dialog.response(gtk.RESPONSE_OK)

	def on_cancel(self, widget, data=None):
		logging.debug("ClaimTableWizard: canceling import")
		self.dialog.response(gtk.RESPONSE_CANCEL)

class ClaimTableOptions:
	def __init__(self):
		pass
