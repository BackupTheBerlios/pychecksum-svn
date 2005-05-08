#! /usr/bin/python
# -*- coding: iso-8859-15 -*-

import sys
import md5
from os import sep, altsep
from os.path import getsize, isfile, isdir, abspath, join, commonprefix, dirname

from SumFile import *

class BaseMd5File(BaseSumFile):
	def __init__(self, filename, treeview):
		BaseSumFile.__init__(self, filename, treeview, 'MD5')
	
	def _compute_md5(self, name):
		try:
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
		except IOError, e:
			print e
			yield ""

class VerifyMd5File(BaseMd5File, VerifySumFile):
	def __init__(self, filename, treeview):
		BaseMd5File.__init__(self, filename, treeview)
		VerifySumFile.__init__(self)
		
	def _read_contents(self):
		d = dirname(self._filename)
		files = {}
		f = file(self._filename)
		for line in f:
			sum = line[:32]
			name = line[34:-1].strip() # we ignore the binary flag
			abs_name = abspath(join(d, name))
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

class CreateMd5File(BaseMd5File):
	def __init__(self, filename, treeview, file_list, ignore_dirs, basedir):
		BaseMd5File.__init__(self, filename, treeview)
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
		self._start = time()
		self._vbytes = 0
		self._vfiles = 0
		
		if self._filename:
			f = file(self._filename, "w+")
		else:
			f = sys.stdout
			
		for name in self._ordered:
			(osum, iter, relname) = self._files[name]
			generator = self._compute_md5(name)
			csum = generator.next()
			while csum == None:
				csum = generator.next()
				yield True
				
			f.write("%s  %s\n" % (csum, relname.replace('\\','/')))
				
		if self._filename:
			f.close()
			
		yield False
