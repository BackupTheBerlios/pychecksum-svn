#! /usr/bin/python
# -*- coding: iso-8859-15 -*-

import gtk
import md5
import os.path
from time import time
filesize = os.path.getsize

BUFFER_SIZE = 262144
STOCK_GOOD = gtk.STOCK_APPLY
STOCK_BAD = gtk.STOCK_CANCEL
STOCK_MISSING = gtk.STOCK_MISSING_IMAGE

def time2human(t):
	m = int(t)/60
	s = t % 60
	if m:
		return "%d m %05.2f s" % (m,s)
	return "%.2f s" % t
	
def size2human(size):
	if size > 1000000000:
		return '%.2gG' % (size/1000000000.)
	elif size > 1000000:
		return '%.2gM' % (size/1000000.)
	elif size > 1000:
		return '%.2gK' % (size/1000.)
	return str(size)
	
class BaseMd5File(object):
	def __init__(self, filename, treeview):
		self._init_treeview(treeview)
		self._filename = filename
		self._files = None
		self._bytes = None
		self._start = 0
		self._show_good = True
		self._show_bad = True
		self._show_missing = True
	
	def _init_treeview(self, treeview):
		self._treeview = treeview
		self._model = gtk.ListStore(str, str)
		
		col = gtk.TreeViewColumn('MD5')
		col.set_sort_column_id(0)
		cell = gtk.CellRendererPixbuf()
		col.pack_start(cell, True)
		col.add_attribute(cell, 'stock-id', 0)
		treeview.append_column(col)
		
		col = gtk.TreeViewColumn('File')
		col.set_sort_column_id(1)
		cell = gtk.CellRendererText()
		col.pack_start(cell, True)
		col.add_attribute(cell, 'text', 1)
		treeview.append_column(col)
	
		treeview.set_model(self._model)
		
	def get_files(self):
		if self._files == None:
			self._read_contents()
		return len(self._files)
		
	def get_bytes(self):
		if self._bytes == None:
			self._read_size()
		return self._bytes
		
	def get_elapsed(self):
		if self._start:
			elapsed = time() - self._start
			return time2human(elapsed)
		return "0"
		
	def get_estimated(self):
		if self._start and self._bytes:
			elapsed = time() - self._start
			estimated = elapsed * self._bytes / self._vbytes
			return time2human(estimated)
		return "0"
		
	def get_remaining(self):
		if self._start and self._bytes:
			elapsed = time() - self._start
			remaining = elapsed * (float(self._bytes) / self._vbytes - 1.)
			return time2human(remaining)
		return "0"
		
	def _compute_md5(self, name):
		f = file(name, "rb")
		m = md5.new()
		line_size = BUFFER_SIZE
		l = f.read(line_size)
		while l != '':
			m.update(l)
			self._vbytes += len(l)
			l = f.read(line_size)
			yield None
			
		self._vfiles += 1
		yield m.hexdigest()
		
	files = property(get_files)
	bytes = property(get_bytes)
	filename = property(lambda self: self._filename)

	vfiles = property(lambda self: self._vfiles)
	vbytes = property(lambda self: self._vbytes)
	elapsed = property(get_elapsed)
	estimated = property(get_estimated)
	remaining = property(get_remaining)

class VerifyMd5File(BaseMd5File):
	def __init__(self, filename, treeview):
		BaseMd5File.__init__(self, filename, treeview)
		self._good = 0
		self._bad = 0
		self._missing = 0
		
	def _read_size(self):
		self.get_files() # make sure the md5 was read
		files = self._files
		bytes = 0
		missing = 0
		
		for name, (sum, iter) in files.items():
			try:
				bytes += os.path.getsize(name)
			except os.error:
				missing += 1
				self._model.set_value(iter, 0, STOCK_MISSING)
				del files[name] # we remove them so we don't check for them a second time
				
		self._missing = missing
		self._bytes = bytes
		
	def _read_contents(self):
		dirname = os.path.dirname(self._filename)
		files = {}
		f = file(self._filename)
		for line in f:
			sum = line[:32]
			name = line[34:-1].strip() # we ignore the binary flag
			abs_name = os.path.abspath(os.path.join(dirname, name))
			iter = self._model.append((None, abs_name))
			files[abs_name] = (sum, iter)
		f.close()
		
		self._vbytes = 0
		self._vfiles = 0
		self._good = 0
		self._bad = 0
		self._files = files
		
	def _filter_row(self, model, path, iter, user_data):
		"""Used by _filter to select the correct rows"""
		new_model, filter = user_data
		pix_id = model.get(iter, 0)[0]
		if pix_id in filter:
			new_model.append((pix_id, model.get(iter, 1)[0]))
			
	def _filter(self):
		filter = []
		if self._show_good:
			filter.append(STOCK_GOOD)
		if self._show_bad:
			filter.append(STOCK_BAD)
		if self._show_missing:
			filter.append(STOCK_MISSING)
			
		model = self._model
		new_model = gtk.ListStore(str, str)
		if filter != []:
			model.foreach(self._filter_row, (new_model, filter))
		self._treeview.set_model(new_model)
		
	def filter_good(self, flag):
		self._show_good = flag
		self._filter()

	def filter_bad(self, flag):
		self._show_bad = flag
		self._filter()
		
	def filter_missing(self, flag):
		self._show_missing = flag
		self._filter()
		
	def verify(self):
		self._start = time()
		self._vbytes = 0
		self._vfiles = 0
		for name, (osum, iter) in self._files.items():
			generator = self._compute_md5(name)
			csum = generator.next()
			while csum == None:
				csum = generator.next()
				yield True
				
			if csum == osum:
				self._good += 1
				self._model.set_value(iter, 0, STOCK_GOOD)
			else:
				self._bad += 1
				self._model.set_value(iter, 0, STOCK_BAD)
				
		yield False
		
	good = property(lambda self: self._good)
	bad = property(lambda self: self._bad)
	missing = property(lambda self: self._missing)
