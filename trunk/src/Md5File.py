#! /usr/bin/python
# -*- coding: iso-8859-15 -*-

import md5
import os.path
filesize = os.path.getsize

BUFFER_SIZE = 262144

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
		
		self._vbytes = 0
		self._vfiles = 0
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
		line_size = BUFFER_SIZE
		l = f.read(line_size)
		while l != '':
			m.update(l)
			self._vbytes += len(l)
			l = f.read(line_size)
			yield None
			
		self._vfiles += 1
		yield m.hexdigest()
		
	def verify(self):
		self._vbytes = 0
		self._vfiles = 0
		for osum, name in self._files.items():
			generator = self._compute_md5(name)
			csum = generator.next()
			while csum == None:
				csum = generator.next()
				yield True
				
			if csum == osum:
				self._good += 1
			else:
				self._bad += 1
		yield False

	files = property(getFiles)
	bytes = property(getBytes)
	good = property(lambda self: self._good)
	bad = property(lambda self: self._bad)
	missing = property(lambda self: self._missing)
	filename = property(lambda self: self._filename)

	vfiles = property(lambda self: self._vfiles)
	vbytes = property(lambda self: self._vbytes)
