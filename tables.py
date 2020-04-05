#!/usr/bin/env python
# Copyright (c) 2016 Jem Scout Limited
#
# All information contained herein is, and remains the property of Jem Scout
# Limited and its suppliers, if any.  The intellectual and technical concepts
# contained herein are proprietary to Jem Scout Limited and its suppliers and
# may be covered by Canadian and Forein Patents, patents in process, and
# are protected by trade secret or copyriht law.  Dissemination of this
# information or reproduction of this material is strictly forbidden unless
# prior written permission is obtained from Jem Scout Limited

import pygtk
pygtk.require("2.0")
import gtk
import gobject
import os
import subprocess
import ConfigParser
import logging
import Queue
import threading
import random
import datetime
import csv
from preferences import preferences
from bs4 import BeautifulSoup
from HTMLParser import *
from urllib2 import urlopen, Request, HTTPError, URLError
from ssl import SSLError
from socket import timeout
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

# 'type' is always a string
# 'flag' sets user mutability, where True = mutable
# 'header' lists the column titles; the following titles are _required_:
#   'Tenure ID', 'Tenure Name', 'Owner', 'Issue Date', 'Expiry Date'
table_layout = {"type": [str, str, str, str, str, str, str, str], \
    "flag": [True, True, False, False, False, False, False, True], \
    "header": ["Group", "Tenure ID", "Tenure Name", "Owner", "Issue Date", "Expiry Date", \
        "Last Updated", "Comments"]}

class ClaimTable(gtk.ListStore):
    required_columns = ["Tenure Name", "Owner", "Issue Date", "Expiry Date", "Last Updated"]
    # ...and "Tenure_ID"

    def __init__(self, *args, **kwargs):
        super(ClaimTable, self).__init__(*args, **kwargs)
        # Supported province dispatch dictionary
        self.province = {"BC": self.update_BC, "YK": self.update_YK, "NV": self.update_NV}

    def __random_user_agent(self):
        user_agent_list = [ \
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/" \
                "22.0.1207.1 Safari/537.1", \
            "Mozilla/5.0 (X11; CrOS i686 2268.111.0) AppleWebKit/536.11 (KHTML, like Gecko)" \
                " Chrome/20.0.1132.57 Safari/536.11", \
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.6 (KHTML, like Gecko) Chrome/" \
                "20.0.1092.0 Safari/536.6", \
            "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.6 (KHTML, like Gecko) Chrome/" \
                "20.0.1090.0 Safari/536.6", \
            "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/" \
                "19.77.34.5 Safari/537.1", \
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/" \
                "19.0.1084.9 Safari/536.5", \
            "Mozilla/5.0 (Windows NT 6.0) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/" \
                "19.0.1084.36 Safari/536.5", \
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/" \
                "19.0.1063.0 Safari/536.3", \
            "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/" \
                "19.0.1063.0 Safari/536.3",\
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_0) AppleWebKit/536.3" \
                " (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3", \
            "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/" \
                "19.0.1062.0 Safari/536.3", \
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/" \
                "19.0.1062.0 Safari/536.3", \
            "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/" \
                "19.0.1061.1 Safari/536.3", \
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/" \
                "19.0.1061.1 Safari/536.3", \
            "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/" \
                "19.0.1061.1 Safari/536.3", \
            "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/" \
                "19.0.1061.0 Safari/536.3", \
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.24 (KHTML, like Gecko) Chrome/" \
                "19.0.1055.1 Safari/535.24", \
            "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/535.24 (KHTML, like Gecko) Chrome/" \
                "19.0.1055.1 Safari/535.24"]
        return random.choice(user_agent_list)

    def __load_html(self, url, to):
        try:
            req = Request(url, headers = {
                "User-Agent": self.__random_user_agent(), \
                "Accept": "text/html,application/xhtml+xml,application/" \
                    "xml;q=0.9,*/*;q=0.8", \
                "Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.3", \
                "Accept-Encoding": "none", \
                "Accept-Language": "en-US,en;q=0.8", \
                "Connection": "keep-alive"})
            handle = urlopen(req, timeout=to)
            html = handle.read()
            handle.close()
        except timeout:
            logging.error("ClaimTable.__load_html(): caught a timeout for url: " + url)
            raise
        except (SSLError, HTTPError, URLError, TypeError, ValueError):
            logging.error("ClaimTable.__load_html(): error loading url: " + url)
            raise

        return html.decode("utf-8")

    def supported(self):
        """ Returns the dictionary of supported provinces """
        return self.province

    def update_entity(self, columns, path, dispatch, to):
        """ Updates a single entity in the claimtable; blocks on __load_html """
        # Validate the table columns
        update = {"column": [], "data": []}
        def find_column(col):
            for i, c  in enumerate(columns):
                if col == c:
                    return i
        try:
            tenure_no = self.get_value(path, find_column("Tenure ID"))
            for col in self.required_columns:
                update["column"].append(int(find_column(col)))
        except IndexError, TypeError:
            logging.error("missing a required column in claimtable!")

        # Dispatch
        self.province[dispatch](update, path, tenure_no, to)

    def update_BC(self, update, path, tenure_no, to):
        BC_prefix = "http://www.mtonline.gov.bc.ca/mtov/tenureDetail.do?tenureNumberIDParam="
        try:
            soup = BeautifulSoup(self.__load_html(BC_prefix + tenure_no, to), "lxml")
        except (timeout, SSLError, HTTPError, URLError, TypeError, ValueError):
            # Re-raise the error to the thread-level
            raise

        try:
            div = soup.find("div", {"id":"print-content"})
            table = div.find_all("table", {"class":"body"})
            tr = table[0].find_all("tr")

            tenure_name = tr[12].find_all("td")[1].string.strip()
            tenure_issue = tr[6].find_all("td")[1].string.strip().upper()
            tenure_expiry = tr[5].find_all("td")[1].string.strip().upper()

            # XXX: there could be more than one owner!
            tr = table[2].find_all("tr")
            tenure_owner = HTMLParser().unescape(tr[1].find_all("td")[2].string.strip())
        except IndexError:
            # Re-raise the error to the thread-level
            raise

        update["data"] = [tenure_name, tenure_owner, tenure_issue, tenure_expiry, \
            datetime.datetime.now().strftime("%Y/%b/%d").upper()]
        for i, c in enumerate(update["data"]):
            self.set_value(path, update["column"][i], c)

    def update_YK(self, update, path, tenure_no, to):
        YK_url = "http://apps.gov.yk.ca/ymcs"
        cap = dict(DesiredCapabilities.PHANTOMJS)
        cap["phantomjs.page.settings.userAgent"] = (self.__random_user_agent())
        try:
            driver = webdriver.PhantomJS(desired_capabilities=cap)
        except WebDriverException:
            logging.error("ClaimTable.update_YK(): unable to find phantomjS.exe!")
            # Re-raise the error to the thread-level
            raise
        driver.set_page_load_timeout(to)
        driver.get(YK_url)

        try:
            reg_type = Select(driver.find_element_by_name("p_t01"))
            reg_type.select_by_visible_text("Quartz")
            claim_status = Select(driver.find_element_by_name("p_t03"))
            claim_status.select_by_visible_text("Active & Pending")
            driver.find_element_by_name("p_t05").send_keys(tenure_no)
            driver.find_element_by_css_selector("a[href*='P1_SEARCH']").click()
            soup = BeautifulSoup(driver.page_source, "html.parser")
            driver.close()
        except NoSuchElementException:
            raise

        try:
            td = soup.find_all("td", {"class":"cellsEven"})
            h = HTMLParser()
            tenure_name = td[3].text + " " + td[4].text
            tenure_owner = h.unescape(td[5].text)
            tenure_issue = td[7].text
            tenure_expiry = td[8].text
        except IndexError:
            # Re-raise the error to the thread-level
            raise

        # Convert dates to numerical year/3-letter month/numerical day format
        ti = tenure_issue.encode("utf-8").split("-")
        tenure_issue = "/".join([ti[0], datetime.date(*[int(i) for i in ti]).strftime("%b"), \
            ti[2]]).upper()
        te = tenure_expiry.encode("utf-8").split("-")
        tenure_expiry = "/".join([te[0], datetime.date(*[int(i) for i in te]).strftime("%b"), \
            te[2]]).upper()

        update["data"] = [tenure_name, tenure_owner, tenure_issue, tenure_expiry, \
            datetime.datetime.now().strftime("%Y/%b/%d").upper()]
        for i, c in enumerate(update["data"]):
            self.set_value(path, update["column"][i], c)

    def update_NV(self, update, path, tenure_no, to):
        NV_url = "https://reports.blm.gov/report/LR2000/77/Pub-MC-Serial-Number-Index"
        cap = dict(DesiredCapabilities.PHANTOMJS)
        cap["phantomjs.page.settings.userAgent"] = (self.__random_user_agent())
        try:
            driver = webdriver.PhantomJS(desired_capabilities=cap)
        except WebDriverException:
            logging.error("ClaimTable.update_NV(): unable to find phantomjS.exe!")
            # Re-raise the error to the thread-level
            raise
        driver.set_page_load_timeout(to)
        driver.get(NV_url)

        try:
            wait = WebDriverWait(driver, 30)
            wait.until(EC.visibility_of_element_located((By.XPATH, "//*[@id='dispReport']")))
            iframe = driver.find_element_by_id("dispReport")
            driver.switch_to.frame(iframe)
            # XXX: this regularly times out, regardless of the wait. why!?
            wait.until(EC.visibility_of_element_located((By.XPATH, "//*[contains(@id,'_7_1_o8')]")))
            driver.find_element_by_xpath("//*[contains(@id,'_7_1_o8')]").click()
            driver.find_element_by_xpath("//*[contains(@id,'_a_1')]").send_keys(tenure_no)
            driver.find_element_by_name("gobtn").click()
            # Fields filled, click 'OK'
            wait.until(EC.visibility_of_element_located((By.XPATH, "//*[contains(@class,'PivotContainer')]")))
            soup = BeautifulSoup(driver.page_source, "html.parser")
            driver.close()
        except TimeoutException, NoSuchElementException:
            raise

        try:
            td = soup.find_all("td", attrs={"class":"mPTDC"})
            tenure_name = td[3].text
            tenure_owner = td[4].text
            tenure_issue = td[9].text.split(" ")[0] # Strip the trailing space
            tenure_issue = datetime.datetime.strptime(tenure_issue, "%m/%d/%Y").strftime("%Y/%b/%d").upper()
            tenure_expiry = td[10].text + "/SEP/02" # Always September 2nd
        except IndexError:
            # Re-raise the error to the thread-level
            raise
        update["data"] = [tenure_name, tenure_owner, tenure_issue, tenure_expiry, \
            datetime.datetime.now().strftime("%Y/%b/%d").upper()]
        for i, c in enumerate(update["data"]):
            self.set_value(path, update["column"][i], c)

    def new_entity(self):
        """ Adds a blank entity to the claimtable """
        row = ["" for i in range(1,self.get_n_columns())]
        # The final row is the foreground text colour
        row.append("#000000")
        self.append(row)

    def delete_entity(self, path, check=True):
        """ Removes the entity from the claimtable """
        self.remove(path)
        # Check for an empty list
        if check and self.__len__() == 0:
            self.new_entity()

    def save_csv(self, filename):
        try:
            f = open(filename, "wb")
        except (OSError, IOError) as e:
            logging.error("ClaimTable.save_csv(): unable to save csv file " + filename)
            logging.error(e)
            error_msg = gtk.MessageDialog(None, 0, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, \
                "Could not save file")
            error_msg.format_secondary_text("Make sure %s is writable and try again." \
                % filename)
            error_msg.run()
            error_msg.destroy()
            return
        writer = csv.writer(f)
        writer.writerow(table_layout["header"])
        for row in self:
            # Don't write the last row, which is the foreground text colour
            writer.writerow(list(row)[:-1])

    # data is {"header1":["row 1", "row 2"], "header2":["row 1", "row 2"]}
    def load_csv(self, data):
        """ Loads a dictionary of data of the format {"header 1":["row 1", ...], ...} into table """
        row = []
        try:
            for a, b in enumerate(data.values()[0]):
                for t, v in enumerate(table_layout["header"]):
                    if v in data.keys():
                        row.append(data[v][a])
                    else:
                        row.append("")
                row.append("#000000")
                self.append(row)
                row = []
        except IndexError:
            logging.error("ClaimTable.load_csv(): no data to import!")
            return

class ClaimTableView(gtk.ScrolledWindow):
    def __init__(self, filename=None, hadjustment=None, vadjustment=None):
        super(ClaimTableView, self).__init__(hadjustment, vadjustment)

        self.pauseflag = False # Pause flag (True/False)
        self.ui = 0 # Update iterator
        self.mutex = threading.Lock() # Update lock

        # Create a ClaimTable with all the columns in the table_dict plus one more for the
        # foreground text colour
        self.claimtable = ClaimTable(str, *[str for t in table_layout["type"]])
        self.treeview = gtk.TreeView(self.claimtable)
        self.treeview.set_grid_lines(gtk.TREE_VIEW_GRID_LINES_BOTH)

        # Load table options file
        self.options = ConfigParser.RawConfigParser()
        ConfigParser.optionsxform = str
        self.filename = filename
        if self.filename is not None:
            # Read the options file if it exists
            if os.access(self.filename + ".ini", os.W_OK):
                self.options.read(self.filename + ".ini")
            else:
                logging.info("Unable to load ClaimTable options file %s", self.filename + ".ini")
        else: # Else initialize a new row
            self.claimtable.new_entity()
        # Validate the options
        self.validate_options()

        # Create a right-click menu
        self.rclick_menu = gtk.Menu()
        menu_new = gtk.MenuItem("New")
        menu_update = gtk.MenuItem("Update")
        menu_update_from = gtk.MenuItem("Update from here")
        menu_delete = gtk.MenuItem("Delete")
        menu_map = gtk.MenuItem("View on map")
        menu_new.connect("activate", self.on_new)
        menu_update.connect("activate", self.on_spawn_update_entity)
        menu_update_from.connect("activate", self.on_update_from_here)
        menu_delete.connect("activate", self.on_delete)
        menu_map.connect("activate", self.on_view_map)
        self.rclick_menu.append(menu_new)
        self.rclick_menu.append(menu_update)
        self.rclick_menu.append(menu_update_from)
        self.rclick_menu.append(menu_delete)
        self.rclick_menu.append(menu_map)
        self.rclick_menu.show_all()
        self.treeview.connect("button-press-event", self.on_click)

        # Build each column w/ appropriate cells
        column = []
        for i, c in enumerate(table_layout["header"]):
            cell = gtk.CellRendererText()
            column.append(gtk.TreeViewColumn(c, cell))
            # Some cells are editable text
            if table_layout["flag"][i] is True:
                cell.set_property("editable", True)
                cell.connect("edited", self.cell_edited, i)
            column[i].add_attribute(cell, "text", i)
            column[i].add_attribute(cell, "foreground", len(table_layout["header"]))
            # Set column sortable, resizable
            column[i].set_sort_column_id(i)
            column[i].set_resizable(True)
            self.treeview.append_column(column[i])
        # Set columns searchable, reorderable
        self.treeview.set_search_column(0)
        self.treeview.set_reorderable(True)

        self.add(self.treeview)
        self.show_all()

    def save_options(self, filename):
        """ Saves the table specific settings """
        try:
            f = open(filename + ".ini", "w")
            self.options.write(f)
        except (OSError, IOError):
            logging.error("Failed to write table options to file " + filename)
            logging.error(e)
        except TypeError:   # No filename (ie. not saved/untitled)
            pass    # Silence the exception

    def validate_options(self):
        """ Validates the table-specific settings """
        province = self.claimtable.supported()
        if not self.options.has_section("Settings"):
            self.options.add_section("Settings")

        # The Key is set to 0, which other dialogs default to
        if not self.options.has_option("Settings", "province"):
            self.options.set("Settings", "province", province.keys()[0])
        if not self.options.get("Settings", "province") in province:
            self.options.set("Settings", "province", province.keys()[0])
        # Validate the timeout parameter

        try:
            if not int(self.options.get("Settings", "timeout")) in range(0, 480):
                self.options.set("Settings", "timeout", 60) 
        except: # Out of range or has_option fails
            self.options.set("Settings", "timeout", 60)

        # Validate the colour settings
        if not self.options.has_option("Settings", "update-colour"):
            self.options.set("Settings", "update-colour", "#257c13")
        try:
            self.update_colour = gtk.gdk.Color(self.options.get("Settings", "update-colour"))
        except:
            self.update_colour = gtk.gdk.Color("#257c13")
        if not self.options.has_option("Settings", "error-colour"):
            self.options.set("Settings", "error-colour", "#9b1f03")
        try:
            self.error_colour = gtk.gdk.Color(self.options.get("Settings", "error-colour"))
        except:
            self.error_colour = gtk.gdk.Color("#9b1f93")
        if not self.options.has_option("Settings", "pause-colour"):
            self.options.set("Settings", "pause-colour", "#989900")
        try:
            self.error_colour = gtk.gdk.Color(self.options.get("Settings", "pause-colour"))
        except:
            self.error_colour = gtk.gdk.Color("#989900")

        # Validate the column mapping parameters
        if not self.options.has_section("Mapping"):
            self.options.add_section("Mapping")
        for key, path in self.options.items("Mapping"):
            if path not in table_layout["header"]:
                self.options.remove_option("Mapping", key)

    def on_click(self, treeview, event):
        """ Catches right-clicks to display a menu """
        if event.button == 3:
            # Get the path
            try:
                self.click_path, column, cellx, celly = \
                    treeview.get_path_at_pos(int(event.x), int(event.y))
                self.rclick_menu.popup(None, None, None, event.button, event.time)
                logging.debug("%s: spawning right-click menu in treeview", self.filename)
            # Not iterable, if event.x or event.y is outside the treeview
            except TypeError:
                return

    def cell_edited(self, cell, path, new_text, column):
        self.mutex.acquire()
        """ Edits the cell in the claimtable """
        logging.debug("%s: ClaimTableView.cell_edited(), path: %s column: %s" \
            % (self.filename, path, column))
        self.claimtable[path][column] = new_text
        self.mutex.release()

    def on_new(self, widget):
        """ Adds a new row to the claimtable """
        self.mutex.acquire()
        logging.debug("\t-> ClaimTableView.on_new()")
        self.claimtable.new_entity()
        self.mutex.release()

    def on_delete(self, widget):
        """ Removes a row from the claimtable """
        self.mutex.acquire()
        logging.debug("\t-> ClaimTableView.on_delete()")
        treemodel = self.treeview.get_model()
        path = treemodel.get_iter(self.click_path[0])
        self.claimtable.delete_entity(path)
        self.mutex.release()

    def on_delete_nocheck(self, ent):
        """ Removes a row from the claimtable, and does not check for an empty table """
        self.mutex.acquire()
        treemodel = self.treeview.get_model()
        path = treemodel.get_iter(ent)
        self.claimtable.delete_entity(path, check=False)
        self.mutex.release()

    def update_entity_thread(self, queue, path, dispatch):
        self.mutex.acquire()
        try:
            queue.put(self.claimtable.update_entity(table_layout["header"], path, dispatch, \
                int(self.options.get("Settings", "timeout"))))
        except (timeout, HTTPError, URLError, TypeError, ValueError, IndexError, \
                WebDriverException) as e:
            logging.error(e)
            queue.put("ERROR")
        self.mutex.release()

    def on_spawn_update_entity(self, widget, path=None):
        """ Spawns a thread that updates a single entity in the claimtable """
        logging.debug("\t-> ClaimTableView.on_spawn_update_entity()")
        treemodel = self.treeview.get_model()
        if not path:
            path = treemodel.get_iter(self.click_path[0])

        # Set update colour on row, set tab label to include 'Updating'
        self.claimtable.set(path, self.claimtable.get_n_columns()-1,
            self.options.get("Settings", "update-colour"))
        o_tab_text = self.retrieve_tab_text()
        self.set_tab_text(o_tab_text + " (Updating)")

        queue = Queue.Queue()
        threading.Thread(target=self.update_entity_thread, \
            args=(queue, path, self.options.get("Settings", "province"))).start()
        while True:
            gobject.main_context_default().iteration(False)
            try:
                if queue.get(block=False) == "ERROR":
                    # Set error colour on row
                    self.claimtable.set(path, self.claimtable.get_n_columns()-1, \
                        self.options.get("Settings", "error-colour"))
                    break
            except Queue.Empty:
                pass
            else:
                # Clear colour on row
                self.claimtable.set(path, self.claimtable.get_n_columns()-1, "#000000")
                break
        self.set_tab_text(o_tab_text)

    def pause_update(self):
        self.pauseflag = True

    def resume_update(self):
        """ Resumes the update in progress """
        logging.debug("%s: resume_update()" % self.filename)
        treemodel = self.treeview.get_model()

        if self.pauseflag is True and self.ui < treemodel.iter_n_children(None):
            self.update_all(bottom=self.ui)

    def on_update_from_here(self, widget, path=None):
        """ Updates all entities from (and including) the clicked entity to the end of the table """
        logging.debug("\t-> ClaimTableView.on_update_from_here()")
        self.update_all(bottom=self.click_path[0])

    def update_all(self, bottom=0):
        """ Updates all entities in the treeview """
        logging.debug("%s: starting update_all()" % self.filename)
        treemodel = self.treeview.get_model()

        self.pauseflag = False
        for self.ui in range(bottom, treemodel.iter_n_children(None)):
            if self.pauseflag is False:
                self.on_spawn_update_entity(None, path=treemodel.get_iter(self.ui))
            elif self.pauseflag is True:
                logging.debug("%s: update_all() paused" % self.filename)
                # Set pause colour on row
                self.claimtable.set(treemodel.get_iter(self.ui), \
                    self.claimtable.get_n_columns()-1, self.options.get("Settings", "pause-colour"))
                break

    def on_view_map(self, widget, path=None):
        """ Spawn the web browser, pointing at a link to the tenure on a map """
        logging.debug("ClaimtTableView.on_view_map()")
        map_dispatch = {"BC": self.view_map_BC, "YK": self.view_map_YK}
        if self.options.get("Settings", "province") not in map_dispatch:
            logging.warning("Province %s not supported" % self.options.get("Settings", "province"))
            return

        treemodel = self.treeview.get_model()
        if not path:
            path = treemodel.get_iter(self.click_path[0])
        # Validate the table columns
        for i, c  in enumerate(table_layout["header"]):
            if c == "Tenure ID":
                try:
                    tenure_no = self.claimtable.get_value(path, i)
                except IndexError, TypeError:
                    logging.error("ClaimtTableView.on_view_map(): missing 'Tenure ID' column" \
                        "in claimtable!")
        if tenure_no:
            map_dispatch[self.options.get("Settings", "province")](tenure_no)

    def view_map_BC(self, tenure_no):
        url = "https://www.mtonline.gov.bc.ca/mtov/showTenure.do?tenureNumberIDParam="
        subprocess.check_call([preferences.get("Web", "browser"), url + tenure_no])


    def view_map_YK(self, tenure_no):
        url = "http://mapservices.gov.yk.ca/Mining/WebMap.aspx?" \
            "runWorkflow=NMRS&minType=quartz&minRequest="
        subprocess.check_call([preferences.get("Web", "browser"), url + tenure_no])     

    def retrieve_tab_text(self):
        notebook = self.get_parent()
        label = notebook.get_tab_label(self).get_children()[0]
        return label.get_text()

    def set_tab_text(self, text):
        notebook = self.get_parent()
        label = notebook.get_tab_label(self).get_children()[0]
        label.set_text(text)
