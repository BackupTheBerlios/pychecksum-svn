#! /usr/bin/python
# -*- coding: iso-8859-15 -*-

GLADE_DIR = ""
GLADE_FILE = "PyCheckSum.glade"
INTERFACE_GNOME = "gnome"
INTERFACE_GTK = "gtk"
INTERFACE_WIN = "win32"

import gtk
from gobject import idle_add as idle_add
import gtk.glade
import os.path
from optparse import OptionParser
import sys
from xml.dom.minidom import parse as dom_parse
from xml.xpath import Evaluate

from Md5File import *

filesize = os.path.getsize

def get_elements_by_attribute(node, name, d):
	elements = []
	for c in node.childNodes:
		if c.nodeType == c.ELEMENT_NODE and c.tagName == name:
			append = True
			for attr, value in d.iteritems():
				if c.hasAttribute(attr) == False or c.getAttribute(attr) != value:
					append = False
					break
			if append:
				elements.append(c)
	return elements

def set_glade_icon(node):
	try:
		xml_icon = get_elements_by_attribute(node, "property", {"name":"icon"})[0]
		glade_path = os.path.join(GLADE_DIR, GLADE_FILE)
		file_name = os.path.join(os.path.dirname(glade_path), xml_icon.childNodes[0].nodeValue)
		xml_icon.childNodes[0].nodeValue = file_name
		return file_name
	except:
		return ""
	
class BaseWindow(object):
	def __init__(self, expanded, interface):
		xml = self._read_glade(interface)
		self.export_glade(xml, expanded)
		
	def _read_glade(self, interface):
		glade_path = os.path.join(GLADE_DIR, GLADE_FILE)
		if interface == INTERFACE_GNOME:
			try:
				xml_doc = dom_parse(glade_path)
				xml_glade_interface = xml_doc.getElementsByTagName("glade-interface")[0]
				xml_gnome_main = get_elements_by_attribute(xml_glade_interface, "widget", {"class":"GnomeApp"})[0]
				
				set_glade_icon(xml_gnome_main)
				
				xml_main = get_elements_by_attribute(xml_glade_interface, "widget", {"class":"GtkWindow", "id":"main"})[0]
				xml_vbox = get_elements_by_attribute(xml_main.getElementsByTagName("child")[0], "widget", {"class":"GtkVBox", "id":"vbox"})[0]
				
				xml_placeholder = xml_gnome_main.getElementsByTagName("placeholder")[0]
				xml_gnome_child = xml_placeholder.parentNode
				
				xml_gnome_child.replaceChild(xml_vbox, xml_placeholder)
				xml_glade_interface.removeChild(xml_main)
				
				xml_gnome_main.attributes["id"].nodeValue = "main"
				
				xml_buf = xml_doc.toxml()
				
				import gnome
				gnome.program_init("PyCheckSum", "0.1")
				xml = gtk.glade.xml_new_from_buffer(xml_buf, len(xml_buf), 'main')
			except:
				print "Can't start as gnome app. Retrying as simple Gtk app..."
				return self._read_glade(INTERFACE_GTK)
		else:
			xml_doc = dom_parse(glade_path)
			xml_glade_interface = xml_doc.getElementsByTagName("glade-interface")[0]
			xml_glade_interface.removeChild(get_elements_by_attribute(xml_glade_interface, "widget", {"class":"GnomeApp"})[0])
			xml_glade_interface.removeChild(get_elements_by_attribute(xml_glade_interface, "requires", {"lib":"gnome"})[0])
			xml_glade_interface.removeChild(get_elements_by_attribute(xml_glade_interface, "requires", {"lib":"bonobo"})[0])
			
			set_glade_icon(get_elements_by_attribute(xml_glade_interface, "widget", {"class":"GtkWindow", "id":"main"})[0])
			
			xml_buf = xml_doc.toxml()
			xml = gtk.glade.xml_new_from_buffer(xml_buf, len(xml_buf), 'main')
		return xml
		
	def export_glade(self, xml, expanded):
		xml.signal_autoconnect(self)
		self.xml = xml
		
		self.window = xml.get_widget('main')
		self.vbox = xml.get_widget('vbox')
		
		self.progress_files = xml.get_widget('progress_files')
		self.progress_bytes = xml.get_widget('progress_bytes')
		
		self.label_lbad = xml.get_widget('label_lbad')
		self.label_lgood = xml.get_widget('label_lgood')
		self.label_lmissing = xml.get_widget('label_lmissing')
		
		self.label_files = xml.get_widget('label_files')
		self.label_bad = xml.get_widget('label_bad')
		self.label_good = xml.get_widget('label_good')
		self.label_missing = xml.get_widget('label_missing')
		self.label_bytes = xml.get_widget('label_bytes')
		self.label_elapsed = xml.get_widget('label_elapsed')
		self.label_estimated = xml.get_widget('label_estimated')
		self.label_remaining = xml.get_widget('label_remaining')
		
		self.treeview_details = xml.get_widget('treeview_details')
		
		self.vbox_details = xml.get_widget('vbox_details')
		self.vbox_details_height = -1
		
		self.frame_filter = xml.get_widget('frame_filter')
		
		xml.get_widget('expander_details').set_expanded(expanded)
	
	def on_expander_details_activate(self, widget):
		if not widget.get_expanded():
			width, height = self.window.get_size()
			self.window.set_size_request(-1, -1)
			self.window.resize(width, height + self.vbox_details_height)
		else:
			width, height = self.window.get_size()
			if self.vbox_details.allocation.height > 1:
				self.vbox_details_height = self.vbox_details.allocation.height
			height -= self.vbox_details.allocation.height
			self.window.set_size_request(width, height)
			self.window.resize(width, height)
		
	def on_main_delete_event(self, widget, event):
		gtk.main_quit()
		return False

	def show_files(self, files):		
		self.label_files.set_markup('<b>%d</b>' % files)
		
	def show_bytes(self, bytes):
		self.label_bytes.set_markup('<b>%s</b>' % size2human(bytes))

	def show_time(self, label, s):
		label.set_markup("<b>%s</b>" % s)

	def show_progress(self, progress, fraction):
		progress.set_fraction(fraction)
		progress.set_text('%d %%' % (fraction*100))
		
	def show_md5_status(self, md5file):
		self.show_time(self.label_elapsed, md5file.elapsed)
		self.show_time(self.label_estimated, md5file.estimated)
		self.show_time(self.label_remaining, md5file.remaining)
		
class CreateWindow(BaseWindow):
	def show_all(self):
		self.window.show()
		
	def create_md5_sum(self, file_list, outfilename, ignore_dirs, basedir):
		self.window.set_title('Creating MD5 sums...')
		yield True # let the appliction start
		
		md5file = CreateMd5File(outfilename, self.treeview_details, file_list, ignore_dirs, basedir)
		self.show_files(md5file.files)
		self.show_bytes(0)
		self.show_md5_status(md5file)
		yield True

		self.show_bytes(md5file.bytes) # force reading the sizes
		self.show_md5_status(md5file)
		
		# here we are finaly verifying the files
		create = md5file.create()
		tfiles = float(md5file.files)
		tbytes = float(md5file.bytes)
		if tbytes > 0 and tfiles > 0:
			while create.next():
				self.show_md5_status(md5file)
				self.show_progress(self.progress_files, md5file.vfiles / tfiles)
				self.show_progress(self.progress_bytes, md5file.vbytes / tbytes)
				yield True
		else:
			print 'nothing to create'
		
		self.print_statistics(md5file)
		self.md5file = md5file
		yield False
		
	def print_statistics(self, md5file):
		print '***********************************'
		if md5file.filename:
			print 'Status for:', os.path.abspath(md5file.filename)
		else:
			print 'Status for: results not saved'
		print '***********************************'
		print 'Files:     ', md5file.files
		print 'Bytes:     ', md5file.bytes
		print 'Time:      ', md5file.elapsed
		print '***********************************'
		
class VerifyWindow(BaseWindow):
	def show_all(self):
		self.label_lbad.show()
		self.label_lgood.show()
		self.label_lmissing.show()
		
		self.label_good.show()
		self.label_bad.show()
		self.label_missing.show()
		
		self.frame_filter.show()
		
		self.window.show()
		
	def on_checkbutton_good_toggled(self, btn, *args):
		self.md5file.filter_good(btn.get_active())
	
	def on_checkbutton_bad_toggled(self, btn, *args):
		self.md5file.filter_bad(btn.get_active())
		
	def on_checkbutton_missing_toggled(self, btn, *args):
		self.md5file.filter_missing(btn.get_active())
		
	def show_bad(self, bad):
		self.label_bad.set_markup("<span foreground='#880000'>%d</span>" % bad)
		
	def show_good(self, good):
		self.label_good.set_markup("<span foreground='#008800'>%d</span>" % good)
		
	def show_missing(self, missing):
		self.label_missing.set_markup("<span foreground='#888800'>%d</span>" % missing)
		
	def show_md5_status(self, md5file):
		BaseWindow.show_md5_status(self, md5file)
		self.show_bad(md5file.bad)
		self.show_good(md5file.good)
		
	def print_statistics(self, md5file):
		print '***********************************'
		print 'Status for:', os.path.abspath(md5file.filename)
		print '***********************************'
		print 'Files:     ', md5file.files
		print 'Good:      ', md5file.good
		print 'Bad:       ', md5file.bad
		print 'Missing:   ', md5file.missing
		print 'Time:      ', md5file.elapsed
		print '***********************************'
		if md5file.missing == 0 and md5file.bad == 0:
			print 'ALL FILES ARE OK'
		elif md5file.bad == 0:
			print 'There are missing files.'
		else:
			print 'There are BAD filles.'
		print '***********************************'
		
	def verify_md5_sum(self, filename):
		"""Cheks a file using idle time."""
		self.window.set_title('Checking: ' + os.path.abspath(filename))
		yield True # let the appliction start
		
		md5file = VerifyMd5File(filename, self.treeview_details)
		self.show_files(md5file.files)
		self.show_bytes(0)
		self.show_md5_status(md5file)
		yield True

		self.show_bytes(md5file.bytes) # force reading the sizes
		self.show_missing(md5file.missing)
		self.show_md5_status(md5file)
		
		# here we are finaly verifying the files
		verify = md5file.verify()
		tfiles = float(md5file.files)
		tbytes = float(md5file.bytes)
		if tbytes > 0 and tfiles > 0:
			while verify.next():
				self.show_md5_status(md5file)
				self.show_progress(self.progress_files, md5file.vfiles / tfiles)
				self.show_progress(self.progress_bytes, md5file.vbytes / tbytes)
				yield True
		else:
			print 'nothing to check'
		
		self.print_statistics(md5file)
		self.frame_filter.set_sensitive(True)
		self.md5file = md5file
		yield False
		
def main():
	usage = '%prog [-x] [-g|-w] (-cFILE | [-oFILE] [-bPATH] file1 [file2])'
	parser = OptionParser(usage = usage)
	
	# the interface 
	parser.add_option("-g", "--gnome", action = "store_const", 
		const = INTERFACE_GNOME, dest="interface", help="use the gnome interface")
	parser.add_option("-w", "--win", action = "store_const",
		const = INTERFACE_WIN, dest="interface", help="use the win32 interface")
	parser.set_defaults(interface = INTERFACE_GTK)
		
	parser.add_option("-d", dest="ignore_dirs", action = "append",
		help="ignore given dir", metavar="DIR", default = [])
	parser.add_option("-x", action = "store_true", dest="expanded",
		help="expand the details on stat-up", default = False)
	parser.add_option("-c", dest="infilename",
		help="verify checksums stored in FILE", metavar="FILE")
	parser.add_option("-o", dest="outfilename",
		help="store checksums in FILE", metavar="FILE")
	parser.add_option("-b", dest="basedir",
		help="compute paths relative to PATH", metavar="PATH")

	(options, args) = parser.parse_args()	
	
	if len(args) == 0 and options.infilename == None:
		parser.error('use -cFILE or provide a list of files')

	# check files against an existing md5sum file
	if options.infilename:
		w = VerifyWindow(options.expanded, options.interface)
		w.show_all()
		idle_add(w.verify_md5_sum(options.infilename).next)
	else:
		w = CreateWindow(options.expanded, options.interface)
		w.show_all()
		idle_add(w.create_md5_sum(args, options.outfilename, options.ignore_dirs, options.basedir).next)
		
	gtk.main()
	
if __name__ == '__main__':
	moduledir = os.path.abspath(os.path.dirname(__file__))
	sys.path.append(moduledir)
	GLADE_DIR = moduledir
	main()
