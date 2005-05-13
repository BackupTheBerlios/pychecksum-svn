#! /usr/bin/python
# -*- coding: iso-8859-15 -*-

import sys
import gtk
import os
from time import time
from os.path import getsize, isfile, isdir, abspath, join, commonprefix, dirname
from md5 import new as md5_new
from binascii import crc32

BUFFER_SIZE = 262144
STOCK_GOOD = gtk.STOCK_APPLY
STOCK_BAD = gtk.STOCK_CANCEL
STOCK_MISSING = gtk.STOCK_DIALOG_WARNING

def time2human(t):
	m = int(t)/60
	s = t % 60
	if m:
		return "%d m %05.2f s" % (m,s)
	return "%.2f s" % t
	
def size2human(size):
	if size > 1000000000:
		return '%.2fG' % (size/1000000000.)
	elif size > 1000000:
		return '%.2fM' % (size/1000000.)
	elif size > 1000:
		return '%.2fK' % (size/1000.)
	return str(size)

class SfvFile(object):
	def compute(name, v):
		f = file(name, "rb")
		s = 0
		line_size = 1000
		l = f.read(line_size)
		while l != '':
			s = crc32(l, s)
			l = f.read(line_size)
		s = "%08X" % s
		print name, s
		v[1] += 1
		yield s
	
	def writeln(out, sum, name): 
		#out.write("%s  %s\n" % (sum, name.replace('\\','/')))
		pass
		
	def readln(line):
		if line[0] == ';':
			return (None, None)
		line = line.rstrip('\n')
		sum = line[-8:]
		name = line[:-9]
		print '; %s "%s"' % (name, sum)
		return (sum, name)
	
	def writehdr(out, ordered, files):
		pass
		
	name = property(lambda self: 'SFV')
	compute = staticmethod(compute)
	writeln = staticmethod(writeln)
	readln = staticmethod(readln)
	writehdr = staticmethod(writehdr)

class Md5File(object):
	def compute(name, v):
		"""Returns the md5 sum of the file 'name'.
		v is a vector that contains the number of
		bytes and files counters."""
		try:
			f = file(name, "rb")
			m = md5_new()
			line_size = BUFFER_SIZE
			l = f.read(line_size)
			while l != '':
				m.update(l)
				v[0] += len(l)
				l = f.read(line_size)
				yield None
				
			v[1] += 1
			yield m.hexdigest()
		except IOError, e:
			print e
			yield ""
	
	def writeln(out, sum, name): 
		out.write("%s  %s\n" % (sum, name.replace('\\','/')))
		
	def readln(line):
		sum = line[:32]
		name = line[34:-1].strip() # we ignore the binary flag
		return (sum, name)
	
	def writehdr(out, *args):
		pass
		
	name = property(lambda self: 'MD5')
	compute = staticmethod(compute)
	writeln = staticmethod(writeln)
	readln = staticmethod(readln)
	writehdr = staticmethod(writehdr)

class BaseSumFile(object):
	def __init__(self, sum, filename, treeview):
		self._sum = sum
		self._init_treeview(treeview, sum.name)
		self._filename = filename
		self._files = None
		self._bytes = None
		self._start = 0
		self._missing = 0
		self._show_missing = True
	
	def _init_treeview(self, treeview, label):
		self._treeview = treeview
		self._model = gtk.ListStore(str, str)
		
		col = gtk.TreeViewColumn(label)
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
		
	def _read_size(self):
		self.get_files() # make sure the md5 was read
		files = self._files
		bytes = 0
		missing = 0
		
		for name, value in files.items():
			sum = value[0]
			iter = value[1]
			try:
				bytes += os.path.getsize(name)
			except os.error:
				missing += 1
				self._model.set_value(iter, 0, STOCK_MISSING)
				del files[name] # we remove them so we don't check for them a second time
				
		self._missing = missing
		self._bytes = bytes
		
	def get_files(self):
		# We call _read_contents only if 
		# we didn't call it already.
		# That is, if _files is None.
		if self._files == None: 
			self._read_contents()
		return len(self._files)
		
	def get_bytes(self):
		# We call _read_size only if 
		# we didn't call it already.
		# That is, if _bytes is None.
		if self._bytes == None:
			self._read_size()
		return self._bytes
		
	def get_elapsed(self):
		if self._start:
			elapsed = time() - self._start
			return time2human(elapsed)
		return "0"
		
	def get_estimated(self):
		if self._start and self._bytes and self._vbytes:
			elapsed = time() - self._start
			estimated = elapsed * self._bytes / self._vbytes
			return time2human(estimated)
		return "0"
		
	def get_remaining(self):
		if self._start and self._bytes and self._vbytes:
			elapsed = time() - self._start
			remaining = elapsed * (float(self._bytes) / self._vbytes - 1.)
			return time2human(remaining)
		return "0"
		
	files = property(get_files)
	bytes = property(get_bytes)
	filename = property(lambda self: self._filename)

	missing = property(lambda self: self._missing)
	vfiles = property(lambda self: self._vfiles)
	vbytes = property(lambda self: self._vbytes)
	elapsed = property(get_elapsed)
	estimated = property(get_estimated)
	remaining = property(get_remaining)

class VerifySumFile(BaseSumFile):
	def __init__(self, sum, filename, treeview):
		BaseSumFile.__init__(self, sum, filename, treeview)
		self._good = 0
		self._bad = 0
		self._show_good = True
		self._show_bad = True
		
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

	def _read_contents(self):
		d = dirname(self._filename)
		files = {}
		f = file(self._filename)
		so = self._sum # _s_um _o_bject
		model = self._model
		for line in f:
			sum, name = so.readln(line)
			if sum:
				abs_name = abspath(join(d, name))
				iter = model.append((None, abs_name))
				files[abs_name] = (sum, iter)
		f.close()
		
		self._vbytes = 0
		self._vfiles = 0
		self._good = 0
		self._bad = 0
		self._files = files
		
	def verify(self):
		compute = self._sum.compute
		self._start = time()
		self._vbytes = 0
		self._vfiles = 0
		v = [self._vbytes, self._vfiles]
		
		for name, (osum, iter) in self._files.items():
			generator = compute(name, v)
			csum = generator.next()
			self._vbytes, self._vfiles = v
			
			while csum == None:
				csum = generator.next()
				self._vbytes, self._vfiles = v
				yield True
				
			if csum == osum:
				self._good += 1
				self._model.set_value(iter, 0, STOCK_GOOD)
			else:
				self._bad += 1
				self._model.set_value(iter, 0, STOCK_BAD)
		
		yield True # for display of the final numbers
		
		yield False

	good = property(lambda self: self._good)
	bad = property(lambda self: self._bad)

class CreateSumFile(BaseSumFile):
	def __init__(self, sum, filename, treeview, file_list, ignore_dirs, basedir):
		BaseSumFile.__init__(self, sum, filename, treeview)
		self._file_list = file_list
		self._ignore_dirs = ignore_dirs
		if basedir and isdir(basedir):
			self._basedir = abspath(basedir)
		else:
			self._basedir = ""

	def _rel_path(self, name, basedir):
		abs_base = abspath(basedir)
		abs_name = abspath(name)
		c = commonprefix((abs_name, abs_base))
		if c:
			m = abs_name[len(c):]
			if m[0] in (sep, altsep):
				m = m[1:]
		else:
			m = abs_name
		return m
		
	def _add_file(self, name, basedir):
		rel_name = self._rel_path(name, basedir)
		iter = self._model.append((None, rel_name))
		self._files[name] = (None, iter, rel_name)
		self._ordered.append(name)
		
	def _filter_dirs(self, dirs):
		for ignore in self._ignore_dirs:
			if ignore in dirs:
				dirs.remove(ignore)
				
	def _read_contents_dir(self, basedir):
		for root, dirs, files in os.walk(basedir):
			files.sort()
			dirs.sort()
			for name in files:
				self._add_file(join(root, name), basedir)
			self._filter_dirs(dirs)
				
	def _read_contents(self):
		self._files = {}
		self._ordered = []
		
		for name in self._file_list:
			if isfile(name):
				self._add_file(name, self._basedir)
			elif isdir(name):
				self._read_contents_dir(name)
			else:
				print "Can't find file or dir: '%s'" % name
				self._model.append((STOCK_MISSING, name))
				
		self._vbytes = 0
		self._vfiles = 0
		
	def create(self):
		compute = self._sum.compute
		writeln = self._sum.writeln
		writehdr = self._sum.writehdr
		
		self._start = time()
		self._vbytes = 0
		self._vfiles = 0
		v = [self._vbytes, self._vfiles]
		
		if self._filename:
			f = file(self._filename, "w+")
		else:
			f = sys.stdout
			
		writehdr(f, self._ordered, self._files)
		
		for name in self._ordered:
			(osum, iter, relname) = self._files[name]
			generator = compute(name, v)
			csum = generator.next()
			self._vbytes, self._vfiles = v
			while csum == None:
				csum = generator.next()
				self._vbytes, self._vfiles = v
				yield True
				
			writeln(f, csum, relname)
				
		if self._filename:
			f.close()
			
		yield False
