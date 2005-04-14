#! /usr/bin/python
# -*- coding: iso-8859-15 -*-

GLADE_DIR = ""
GLADE_FILE = "PyCheckSum.glade"

import gtk
from gobject import idle_add as idle_add
import gtk.glade
import os.path
from optparse import OptionParser

from Md5File import *

filesize = os.path.getsize

class MainWindow:
	def __init__(self):
		glade_path = os.path.join(GLADE_DIR, GLADE_FILE)
		xml = gtk.glade.XML(glade_path, 'main')
		self.export_glade(xml)
		self.tries = 0
		
	def export_glade(self, xml):
		xml.signal_autoconnect(self)
		self.xml = xml
		self.window = xml.get_widget('main')
		self.progress_files = xml.get_widget('progress_files')
		self.progress_bytes = xml.get_widget('progress_bytes')
		self.label_files = xml.get_widget('label_files')
		self.label_bad = xml.get_widget('label_bad')
		self.label_good = xml.get_widget('label_good')
		self.label_missing = xml.get_widget('label_missing')
		self.label_bytes = xml.get_widget('label_bytes')
		self.vbox = xml.get_widget('vbox')
		self.treeview_details = xml.get_widget('treeview_details')
		self.scrolledwindow_details = xml.get_widget('scrolledwindow_details')
		self.scrolledwindow_height = -1
		
	def on_expander_details_activate(self, widget):
		if not widget.get_expanded():
			width, height = self.window.get_size()
			self.window.set_size_request(-1, -1)
			self.window.resize(width, height + self.scrolledwindow_height)
		else:
			width, height = self.window.get_size()
			if self.scrolledwindow_details.allocation.height > 1:
				self.scrolledwindow_height = self.scrolledwindow_details.allocation.height
			height -= self.scrolledwindow_details.allocation.height
			self.window.set_size_request(width, height)
			self.window.resize(width, height)
		
	def on_main_delete_event(self, widget, event):
		self.tries -= 1
		if self.tries > 0:
			return True
		else:
			gtk.main_quit()
			return False

	def show_files(self, files):		
		self.label_files.set_markup('<b>%d</b>' % files)
		
	def show_bytes(self, bytes):
		self.label_bytes.set_markup('<b>%s</b>' % size2human(bytes))
		
	def show_bad(self, bad):
		self.label_bad.set_markup("<span foreground='#880000'>%d</span>" % bad)
		
	def show_good(self, good):
		self.label_good.set_markup("<span foreground='#008800'>%d</span>" % good)
		
	def show_missing(self, missing):
		self.label_missing.set_markup("<span foreground='#888800'>%d</span>" % missing)
		
	def show_md5_status(self, md5file):
		self.show_bad(md5file.bad)
		self.show_good(md5file.good)
		
	def show_progress(self, progress, fraction):
		progress.set_fraction(fraction)
		progress.set_text('%d %%' % (fraction*100))
		
	def print_statistics(self, md5file):
		print '***********************************'
		print 'Status for:', os.path.abspath(md5file.filename)
		print '***********************************'
		print 'Files:     ', md5file.files
		print 'Good:      ', md5file.good
		print 'Bad:       ', md5file.bad
		print 'Missing:   ', md5file.missing
		print '***********************************'
		if md5file.missing == 0 and md5file.bad == 0:
			print 'ALL FILES ARE OK'
		elif md5file.bad == 0:
			print 'There are missing files.'
		else:
			print 'There are BAD filles.'
		print '***********************************'
		
	def check_md5_sum(self, filename):
		"""Cheks a file using idle time."""
		self.window.set_title('Checking: ' + os.path.abspath(filename))
		yield True # let the appliction start
		
		md5file = Md5File(filename)
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
		yield False
		
def main():
	usage = '%prog [options] (-c FILE | file1 [file2])'
	parser = OptionParser(usage = usage)
	parser.add_option("-q", "--quiet",
		action="store_false", dest="verbose", default=True,
		help="don't print status messages to stdout")
	parser.add_option("-c", dest="filename",
		help="verify checksums stored in FILE", metavar="FILE")

	(options, args) = parser.parse_args()	
	
	if len(args) == 0 and options.filename == None:
		parser.error('use -c FILE or provide a list of files')

	# check files against an existing md5sum file
	if options.filename:
		w = MainWindow()
		w.window.show_all()
		idle_add(w.check_md5_sum(options.filename).next)
		gtk.main()
	
if __name__ == '__main__':
	main()
