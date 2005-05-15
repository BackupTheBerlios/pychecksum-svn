#! /usr/bin/python
# -*- coding: iso-8859-15 -*-

GLADE_DIR = ""
GLADE_FILE = "PyCheckSum.glade"
INTERFACE_GNOME = "gnome"
INTERFACE_GTK = "gtk"
ALGO_MD5 = "md5"
ALGO_SFV = "sfv"

import gtk
from gobject import idle_add as idle_add
import gtk.glade
import os.path
from optparse import OptionParser
import sys
from xml.dom.minidom import parse as dom_parse

from SumFile import *

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
		
	def show_status(self, sumfile):
		self.show_time(self.label_elapsed, sumfile.elapsed)
		self.show_time(self.label_estimated, sumfile.estimated)
		self.show_time(self.label_remaining, sumfile.remaining)
		
	def show_all_progress(self, sumfile, tfiles, tbytes):
		self.show_progress(self.progress_files, sumfile.vfiles / tfiles)
		self.show_progress(self.progress_bytes, sumfile.vbytes / tbytes)
		
		s = '%d%%' % (100. * sumfile.vbytes / tbytes)
		if sumfile.filename:
			s += ' - ' + os.path.basename(sumfile.filename)
		self.window.set_title(s)
		
class CreateWindow(BaseWindow):
	def show_all(self):
		self.window.show()
		
	def create_sum(self, sum, file_list, outfilename, ignore_dirs, basedir):
		self.window.set_title('Creating checksums...')
		yield True # let the appliction start
		
		sumfile = CreateSumFile(sum, outfilename, self.treeview_details, file_list, ignore_dirs, basedir)
		self.show_files(sumfile.files)
		self.show_bytes(0)
		self.show_status(sumfile)
		yield True

		self.show_bytes(sumfile.bytes) # force reading the sizes
		self.show_status(sumfile)
		
		# here we are finaly verifying the files
		create = sumfile.create()
		tfiles = float(sumfile.files)
		tbytes = float(sumfile.bytes)
		if tbytes > 0 and tfiles > 0:
			while create.next():
				self.show_status(sumfile)
				self.show_all_progress(sumfile, tfiles, tbytes)
				yield True
		else:
			print 'nothing to create'
		
		self.print_statistics(sumfile)
		self.sumfile = sumfile
		yield False
		
	def print_statistics(self, sumfile):
		print '***********************************'
		if sumfile.filename:
			print 'Status for:', os.path.abspath(sumfile.filename)
		else:
			print 'Status for: results not saved'
		print '***********************************'
		print 'Files:     ', sumfile.files
		print 'Bytes:     ', sumfile.bytes
		print 'Time:      ', sumfile.elapsed
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
		self.sumfile.filter_good(btn.get_active())
	
	def on_checkbutton_bad_toggled(self, btn, *args):
		self.sumfile.filter_bad(btn.get_active())
		
	def on_checkbutton_missing_toggled(self, btn, *args):
		self.sumfile.filter_missing(btn.get_active())
		
	def show_bad(self, bad):
		self.label_bad.set_markup("<span foreground='#880000'>%d</span>" % bad)
		
	def show_good(self, good):
		self.label_good.set_markup("<span foreground='#008800'>%d</span>" % good)
		
	def show_missing(self, missing):
		self.label_missing.set_markup("<span foreground='#888800'>%d</span>" % missing)
		
	def show_status(self, sumfile):
		BaseWindow.show_status(self, sumfile)
		self.show_bad(sumfile.bad)
		self.show_good(sumfile.good)
		
	def print_statistics(self, sumfile):
		print '***********************************'
		print 'Status for:', os.path.abspath(sumfile.filename)
		print '***********************************'
		print 'Files:     ', sumfile.files
		print 'Good:      ', sumfile.good
		print 'Bad:       ', sumfile.bad
		print 'Missing:   ', sumfile.missing
		print 'Time:      ', sumfile.elapsed
		print '***********************************'
		if sumfile.missing == 0 and sumfile.bad == 0:
			print 'ALL FILES ARE OK'
		elif sumfile.bad == 0:
			print 'There are missing files.'
		else:
			print 'There are BAD filles.'
		print '***********************************'
		
	def verify_sum(self, sum, filename):
		"""Cheks a file using idle time."""
		self.window.set_title('0% - ' + os.path.basename(filename))
		yield True # let the appliction start
		
		sumfile = VerifySumFile(sum, filename, self.treeview_details)
		self.show_files(sumfile.files)
		self.show_bytes(0)
		self.show_status(sumfile)
		yield True

		self.show_bytes(sumfile.bytes) # force reading the sizes
		self.show_missing(sumfile.missing)
		self.show_status(sumfile)
		
		# here we are finaly verifying the files
		verify = sumfile.verify()
		tfiles = float(sumfile.files)
		tbytes = float(sumfile.bytes)
		if tbytes > 0 and tfiles > 0:
			while verify.next():
				self.show_status(sumfile)
				self.show_all_progress(sumfile, tfiles, tbytes)
				yield True
		else:
			print 'nothing to check'
		
		self.print_statistics(sumfile)
		self.frame_filter.set_sensitive(True)
		self.sumfile = sumfile
		yield False
		
def main():
	platform_win32 = sys.platform.startswith("win")

	if platform_win32:
		usage = """
\t%prog [-x] [--md5|--sfv] -cFILE
\t%prog [-x] [--md5|--sfv] [-oFILE] [-bPATH] file1 [file2] [-i PATH1]
\t%prog --register
\t%prog --unregister
\t%prog (-h|--help)"""
	else:
		usage = '%prog [-xg] [--md5|--sfv] (-cFILE | [-oFILE] [-bPATH] file1 [file2] [-i PATH1])'
	parser = OptionParser(usage = usage)

	# the interface
	# on windows we can't have gnome so we disable all interfac options!
	if not platform_win32:
		parser.add_option("-g", "--gnome", action = "store_const", 
			const = INTERFACE_GNOME, dest="interface", help="use the gnome interface")
	parser.set_defaults(interface = INTERFACE_GTK)

	# on windows, we need to (un)register with the registry
	if platform_win32:
		parser.add_option("", "--register", action = "store_true", 
			dest="register", help="register with the REGISTRY")
		parser.add_option("", "--unregister", action = "store_true", 
			dest="unregister", help="unregister from the REGISTRY")
		
	parser.add_option("", "--md5", action = "store_const", 
		const = ALGO_MD5, dest="algo", help="check or create MD5's")
	parser.add_option("", "--sfv", action = "store_const", 
		const = ALGO_SFV, dest="algo", help="check or create SFV's")
	parser.set_defaults(algo = ALGO_MD5)
	
	parser.add_option("-i", dest="ignore_dirs", action = "append",
		help="ignore given dir", metavar="DIR", default = [])
	parser.add_option("-x", action = "store_true", dest="expanded",
		help="expand the details on stat-up", default = False)
	parser.add_option("-c", dest="infilename",
		help="verify checksums stored in FILE", metavar="FILE")
	parser.add_option("-o", dest="outfilename",
		help="store checksums in FILE", metavar="FILE")
	parser.add_option("-b", dest="basedir",
		help="compute paths relative to PATH", metavar="PATH")

	parser.add_option("-f", dest="singlefile",
		help="compute PATH's MD5 and store it in PATH.md5", metavar="PATH")
	parser.add_option("-d", dest="singledir",
		help="compute PATH's MD5 and store it in PATH.md5", metavar="PATH")
	
	(options, args) = parser.parse_args()	

	finished = False
	
	if platform_win32:
		import Register
		
		# (un)register from registry
		if options.register and options.unregister:
			parser.error('please use only one of the --register or --unregister, but not both')

		if options.register:
			Register.register(os.path.abspath(__file__))
			finished = True
		elif options.unregister:
			Register.unregister()
			finished = True

	if not finished:
		if options.algo == ALGO_MD5:
			sum = Md5File()
		else:
			sum = SfvFile()
			
		if options.singlefile:
			# create sum for a single file
			basedir = os.path.dirname(options.singlefile)
			outfilename = options.singlefile + ".md5"
			w = CreateWindow(options.expanded, options.interface)
			w.show_all()
			idle_add(w.create_sum(sum, [options.singlefile], outfilename, None, basedir).next)
		
		elif options.singledir:
			# create sum for a single dir
			basedir = '.'
			options.singledir = options.singledir.rstrip("\\").rstrip("/").rstrip('"')
			outfilename = os.path.join(options.singledir, os.path.basename(options.singledir)) + ".md5"
			os.remove(outfilename)
			w = CreateWindow(options.expanded, options.interface)
			w.show_all()
			idle_add(w.create_sum(sum, [options.singledir], outfilename, options.ignore_dirs, basedir).next)
		
		else:
			if len(args) == 0 and options.infilename == None:
				parser.error('use -cFILE or provide a list of files')

			# check files against an existing md5sum file
			if options.infilename:
				w = VerifyWindow(options.expanded, options.interface)
				w.show_all()
				idle_add(w.verify_sum(sum, options.infilename).next)
			
			else:
				w = CreateWindow(options.expanded, options.interface)
				w.show_all()
				if options.outfilename:
					try:
						os.remove(options.outfilename)
					except OSError:
						pass
				idle_add(w.create_sum(sum, args, options.outfilename, options.ignore_dirs, options.basedir).next)
		gtk.main()
	
if __name__ == '__main__':
	moduledir = os.path.abspath(os.path.dirname(__file__))
	sys.path.append(moduledir)
	GLADE_DIR = moduledir
	main()
