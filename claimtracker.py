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
from dialogs import *
from tables import *
from preferences import preferences

version = "0.9.2"

def load_status_icon(path, size_x, size_y, stock):
	if os.access(path, os.R_OK):
		pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(path, size_x, size_y)
		return gtk.status_icon_new_from_pixbuf(pixbuf)
	else:
		# Can't find icon file
		logging.warning("cannot find icon file: " + path)
		return gtk.status_icon_new_from_stock(stock)

def load_image(path, size_x, size_y, stock):
	if os.access(path, os.R_OK):
		pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(path, size_x, size_y)
		return gtk.image_new_from_pixbuf(pixbuf)
	else:
		# Can't find image
		logging.warning("cannot find image file: " + path)
		return gtk.image_new_from_stock(stock, gtk.ICON_SIZE_MENU)

class MainWindow:
	def delete_event(self, widget, event, data=None):
		""" Prompts for unsaved changes when user closes the window """ 
		# XXX: Are you sure you want to quit?
		preferences.save()
		return False

	def destroy(self, widget, data=None):
		gtk.main_quit()
		logging.info("Terminated")

	def __init__(self):
		# Create window
		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.window.set_title = ("claimtracker")
		self.window.connect("delete-event", self.delete_event)
		self.window.connect("destroy", self.destroy)

		# Set window icon:
		icon_path = os.path.realpath("." + "\icon.png") # Read file if it exists
		if os.access(icon_path, os.R_OK):
			self.window.set_icon_from_file("icon.png")

		# Load global preferences
		preferences_path = os.path.realpath(".") + "\claimtracker.ini"
		preferences.load(preferences_path)
		preferences.validate()

		logging.info("Claimtracker initialized...")

		self.window.set_default_size(int(preferences.get("Window", "width")), \
			int(preferences.get("Window", "height")))
		if int(preferences.get("Window", "min_to_tray")) == 1:
			self.set_minimize_to_tray()

		# Container
		self.container = gtk.VBox(gtk.FALSE, 0)
		self.window.add(self.container)

		# Menu bar
		self.menubar = gtk.MenuBar()
		self.container.pack_start(self.menubar, False, False, 0)

		# File menu
		file_menu = gtk.Menu()
		menu_new_table = gtk.MenuItem(label = "New Table")
		menu_open = gtk.MenuItem(label="Open File")
		menu_close_table = gtk.MenuItem(label="Close Table")
		menu_save_table = gtk.MenuItem(label="Save Table")
		menu_exit = gtk.MenuItem(label="Exit")
		menu_new_table.connect("activate", self.on_new_table)
		menu_open.connect("activate", self.on_open)
		menu_save_table.connect("activate", self.on_save)
		menu_close_table.connect("activate", self.on_close_table)
		menu_exit.connect("activate", self.destroy)
		file_menu.append(menu_new_table)
		file_menu.append(menu_open)
		file_menu.append(menu_close_table)
		file_menu.append(menu_save_table)
		file_menu.append(gtk.SeparatorMenuItem())
		file_menu.append(menu_exit)
		file_m = gtk.MenuItem(label="File")
		file_m.set_submenu(file_menu)
		self.menubar.append(file_m)

		# Edit menu
		edit_menu = gtk.Menu()
		menu_preferences = gtk.MenuItem(label="Preferences")
		menu_preferences.connect("activate", PreferencesDialog)
		edit_menu.append(menu_preferences)
		edit_m = gtk.MenuItem(label="Edit")
		edit_m.set_submenu(edit_menu)
		self.menubar.append(edit_m)

		# Table menu
		table_menu = gtk.Menu()
		menu_update_all = gtk.MenuItem(label="Update All")
		menu_pause_update = gtk.MenuItem(label="Pause Update")
		menu_resume_update = gtk.MenuItem(label="Resume Update")
		menu_import_wizard = gtk.MenuItem(label="Import Wizard")
		menu_update_all.connect("activate", self.on_update_all)
		menu_pause_update.connect("activate", self.on_pause_update)
		menu_resume_update.connect("activate", self.on_resume_update)
		menu_import_wizard.connect("activate", self.on_import_wizard)
		table_menu.append(menu_update_all)
		table_menu.append(menu_pause_update)
		table_menu.append(menu_resume_update)
		table_menu.append(gtk.SeparatorMenuItem())
		table_menu.append(menu_import_wizard)
		table_m = gtk.MenuItem(label="Table")
		table_m.set_submenu(table_menu)
		self.menubar.append(table_m)

		# Help menu
		help_menu = gtk.Menu()
		menu_help_topics = gtk.MenuItem(label="Help Topics")
		menu_help_topics.connect("activate", self.help_topics)
		menu_about = gtk.MenuItem(label="About")
		menu_about.connect("activate", self.help_about)
		menu_check_for_updates = gtk.MenuItem(label="Check for Updates")
		menu_check_for_updates.connect("activate", self.on_check_for_updates)
		help_menu.append(menu_help_topics)
		help_menu.append(menu_about)
		help_menu.append(gtk.SeparatorMenuItem())
		help_menu.append(menu_check_for_updates)
		help_m = gtk.MenuItem(label="Help")
		help_m.set_submenu(help_menu)
		self.menubar.append(help_m)

		# Tabbed tables
		self.notebook = gtk.Notebook()
		self.notebook.set_tab_pos(gtk.POS_TOP)
		self.container.pack_end(self.notebook, True, True, 0)

		self.on_new_table(None, None)

		self.window.show_all()

	def check_window_state(self):
		mask = gtk.gdk.WINDOW_STATE_MAXIMIZED
		return self.window.get_window().get_state() & mask == mask

	def minimize_to_tray(self, widget, event, data=None):
		""" Minimizes window to tray (statusicon) """
		if event.changed_mask & gtk.gdk.WINDOW_STATE_ICONIFIED:
			if event.new_window_state & gtk.gdk.WINDOW_STATE_ICONIFIED:
				logging.debug("minimize to tray")
				self.window_state = self.check_window_state()
				self.statusicon.set_visible(True)
				self.window.hide_all()

	def return_from_tray(self, event):
		""" Returns window from tray (statusicon) """
		logging.debug("return from tray")
		if self.window_state: # Was the window previously maximized?
			self.window.maximize()
		self.window.show_all()
		self.window.present()
		self.statusicon.set_visible(False)

	def set_minimize_to_tray(self):
		""" Turns on statusicon menu and window-to-statusicon callbacks"""
		self.statusicon = gtk.StatusIcon()
		icon_path = os.path.realpath("." + "\\icon.png")
		self.statusicon = load_status_icon(icon_path, 128, 128, gtk.STOCK_GOTO_TOP)
		self.statusicon.set_tooltip("Claimtracker")
		self.statusicon.connect("activate", self.return_from_tray)
		self.window.connect("window-state-event", self.minimize_to_tray)
		self.statusicon.set_visible(False)

	def on_new_table(self, widget, data=None):
		""" File->New Table """
		claimtable = ClaimTableView(data)

		# Build a label with a status icon and close button
		hbox = gtk.HBox()
		label = gtk.Label("untitled")
		hbox.pack_start(label, True, True, 0)
		close_button = gtk.Button()
		close_button.set_relief(gtk.RELIEF_NONE)
		close_button.set_focus_on_click(False)
		icon_path = os.path.realpath("." + "\\close.png")
		close_button.add(load_image(icon_path, 12, 12, gtk.STOCK_CLOSE))
		close_button.connect("clicked", self.on_close_table, claimtable)
		hbox.pack_end(close_button, False, False, 0)
		hbox.show_all()

		# Add a claimtable with hbox label to notebook
		tab_id = self.notebook.append_page(claimtable, hbox)
		self.notebook.set_tab_reorderable(claimtable, True)
		self.notebook.set_current_page(tab_id)
		self.notebook.show()
		return claimtable

	def on_save(self, widget, data=None):
		""" File->Save Table """
		FileDialog("Select file...", None, gtk.FILE_CHOOSER_ACTION_SAVE, \
			(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK), \
			self.save_file, 0).run()

	def save_file(self, widget=None, data=None):
		filename = widget.get_filename()
		widget.destroy()
		claimtable = self.notebook.get_nth_page(self.notebook.get_current_page())
		_, fil = os.path.split(filename)
		claimtable.set_tab_text(fil)
		claimtable.claimtable.save_csv(filename)
		claimtable.save_options(filename)

	def on_open(self, widget, data=None):
		""" File->Open Table """
		FileDialog("Select file...", None, gtk.FILE_CHOOSER_ACTION_OPEN, \
			(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK), \
			self.open_file, 0).run()

	def open_file(self, widget=None, data=None):
		filename = widget.get_filename()
		widget.destroy()
		ClaimTableWizard(self, filename)

	def on_close_table(self, widget, data=None):
		""" File->Close Table """
		# Check if called from the menu or from the tab's close button
		if isinstance(widget, gtk.Button):
			tab_id = self.notebook.page_num(data)
		elif isinstance(widget, gtk.MenuItem):
			tab_id = self.notebook.get_current_page()
		claimtable = self.notebook.get_nth_page(tab_id)
		filename = claimtable.filename

		# XXX: Check for save status

		self.notebook.remove_page(tab_id)
		claimtable.destroy()

		# If no more tables are open, exit the program
		if self.notebook.get_n_pages() == 0:
			self.window.destroy()

	def on_pause_update(self, widget, data=None):
		"""Table->Pause Update"""
		claimtable = self.notebook.get_nth_page(self.notebook.get_current_page())
		claimtable.pause_update()

	def on_update_all(self, widget, data=None):
		""" Table->Update All"""
		claimtable = self.notebook.get_nth_page(self.notebook.get_current_page())
		claimtable.update_all()

	def on_resume_update(self, widget, data=None):
		claimtable = self.notebook.get_nth_page(self.notebook.get_current_page())
		claimtable.resume_update()		

	def on_import_wizard(self, widget, data=None):
		tab_id = self.notebook.get_current_page()
		claimtable = self.notebook.get_nth_page(tab_id)
		filename = claimtable.filename
		if filename:
			ClaimTableWizard(self, filename, claimtable)
		else:
			error_msg = gtk.MessageDialog(self.window, 0, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, \
				"No file open!")
			error_msg.format_secondary_text("Save your file and try again.")
			error_msg.run()
			error_msg.destroy()

	def on_check_for_updates(self, widget, data=None):
		# XXX: This doesn't actually do anything for now!
		update_msg = gtk.MessageDialog(self.window, 0, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, \
			"You're up-to-date!")
		update_msg.format_secondary_text("Claimtracker %s is currently the newest version " \
			"available." % version)
		update_msg.run()
		update_msg.destroy()

	def help_topics(self, widget, data=None):
		url = "file://" + os.path.realpath("." + "\\doc\\index.html")
		subprocess.check_call([preferences.get("Web", "browser"), url])

	def help_about(self, widget, data=None):
		url = "file://" + os.path.realpath("." + "\doc\\topics\\About.html")
		subprocess.check_call([preferences.get("Web", "browser"), url])

	def main(self):
		gtk.main()

if __name__ == "__main__":
	claimtracker = MainWindow()
	claimtracker.main()
