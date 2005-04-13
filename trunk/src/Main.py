#! /usr/bin/python
# -*- coding: iso-8859-15 -*-

GLADE_DIR = ""
GLADE_FILE = "PyCheckSum.glade"

import gtk
from gobject import idle_add as idle_add
import gtk.glade
import os.path
import md5
from optparse import OptionParser

filesize = os.path.getsize

def size2human(size):
	if size > 1000000000:
		return '%.2gG' % (size/1000000000.)
	elif size > 1000000:
		return '%.2gM' % (size/1000000.)
	elif size > 1000:
		return '%.2gK' % (size/1000.)
	return str(size)
	
class Md5File(object):
	def __init__(self, filename):
		self._filename = filename
		self._files = None
		self._bytes = None
		self._good = 0
		self._bad = 0
		self._missing = 0
	
	def _read_size(self):
		self.getFiles() # make sure the md5 was read
		files = self._files
		bytes = 0
		missing = 0
		
		for sum, name in files.items():
			try:
				bytes += os.path.getsize(name)
			except os.error:
				missing += 1
				del files[sum] # we remove them so we don't check for them a second time
				
		self._missing = missing
		self._bytes = bytes
		
	def _read_contents(self):
		dirname = os.path.dirname(self._filename)
		files = {}
		f = file(self._filename)
		for line in f:
			sum = line[:32]
			name = line[34:-1].strip() # we ignore the binary flag
			files[sum] = os.path.join(dirname, name)
		f.close()
		
		self._good = 0
		self._bad = 0
		self._files = files
		
	def getFiles(self):
		if self._files == None:
			self._read_contents()
		return len(self._files)
		
	def getBytes(self):
		if self._bytes == None:
			self._read_size()
		return self._bytes
		
	def _compute_md5(self, name):
		f = file(name)
		m = md5.new()
		line_size = 100000
		l = f.read(line_size)
		while l != '':
			m.update(l)
			l = f.read(line_size)
		return m.hexdigest()
		
	def verify(self):
		for osum, name in self._files.items():
			csum = self._compute_md5(name)
			if csum == osum:
				self._good += 1
			else:
				self._bad += 1
			yield os.path.getsize(name)
		yield -1
		return
		
	files = property(getFiles)
	bytes = property(getBytes)
	good = property(lambda self: self._good)
	bad = property(lambda self: self._bad)
	missing = property(lambda self: self._missing)
	filename = property(lambda self: self._filename)
		
class MainWindow:
	def __init__(self):
		glade_path = os.path.join(GLADE_DIR, GLADE_FILE)
		xml = gtk.glade.XML(glade_path, 'main')
		self.expose_glade(xml)
		self.tries = 0
		
	def expose_glade(self, xml):
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
		self.window.set_title('Checking: ' + filename)
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
		vfiles = 0
		vbytes = 0
		if tbytes > 0 and tfiles > 0:
			while True:
				bytes = verify.next()
				if bytes == -1:
					break
				vfiles += 1
				vbytes += bytes
				self.show_md5_status(md5file)
				self.show_progress(self.progress_files, vfiles / tfiles)
				self.show_progress(self.progress_bytes, vbytes / tbytes)
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
