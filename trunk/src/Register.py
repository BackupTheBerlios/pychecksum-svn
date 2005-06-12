#! /usr/bin/python
# -*- coding: iso-8859-15 -*-

import _winreg
import os
import sys

class SumFile(object):
	def __init__(self,
				 script = '',
				 args = '',
				 menu_check = 'Verify',
				 menu_create = 'Generate MD5 checksum',
				 extension = '.md5',
				 icon = 'shell32.dll,104',
				 info = 'md5 checksum',
				 check_key = 'md5file'):
		
		self.__menu_check = menu_check
		self.__menu_create = menu_create
		self.__extension = extension
		self.__icon = icon
		self.__info = info
		self.__check_key = check_key

		self.__check_command_key = 'shell\\%s\\command' % menu_check
		self.__check_command = '%s\\pythonw.exe  "%s" %s -c "%%1"' % (sys.exec_prefix, script, args)
		
		self.__create_command_key_uninstall = 'shell\\%s' % menu_create
		self.__create_command_key = 'shell\\%s\\command' % menu_create
		self.__create_command_file = '%s\\pythonw.exe "%s" %s -f "%%1"' % (sys.exec_prefix, script, args)
		self.__create_command_dir = '%s\\pythonw.exe "%s" %s -d "%%1"' % (sys.exec_prefix, script, args)
		
	def register(self):
		print "Registering %s ..." % self.__extension[1:], 

		h = _winreg.CreateKey(_winreg.HKEY_CLASSES_ROOT, self.__extension)
		_winreg.SetValueEx(h, None, 0, _winreg.REG_SZ, self.__check_key)

		h = _winreg.CreateKey(_winreg.HKEY_CLASSES_ROOT, self.__check_key)
		_winreg.SetValueEx(h, None, 0, _winreg.REG_SZ, self.__info)

		h1 = _winreg.CreateKey(h, 'DefaultIcon')
		_winreg.SetValueEx(h1, None, 0, _winreg.REG_SZ, self.__icon)

		h1 = _winreg.CreateKey(h, self.__check_command_key)
		_winreg.SetValueEx(h1, None, 0, _winreg.REG_SZ, self.__check_command)

		# write the handler for single files
		h = _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT, '*')
		h = _winreg.CreateKey(h, self.__create_command_key)
		_winreg.SetValueEx(h, None, 0, _winreg.REG_SZ, self.__create_command_file)

		# write the handler for directories
		h = _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT, 'Directory')
		h = _winreg.CreateKey(h, self.__create_command_key)
		_winreg.SetValueEx(h, None, 0, _winreg.REG_SZ, self.__create_command_dir)

		print 'Done.'

	def __delete_key(self, base_key, sub_key):
		try:
			key = _winreg.OpenKey(base_key, sub_key)
			while True:
				# delete subkeys of the sub_key
				try:
					while True:
						self.__delete_key(key, _winreg.EnumKey(key, 0))
				except EnvironmentError:
					break
			_winreg.DeleteKey(base_key, sub_key)
		except EnvironmentError:
			pass

	def unregister(self):
		print "Unregistering %s ..." % self.__extension[1:], 
		self.__delete_key(_winreg.HKEY_CLASSES_ROOT, self.__extension)
		self.__delete_key(_winreg.HKEY_CLASSES_ROOT, self.__check_key)

		h = _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT, '*')
		self.__delete_key(h, self.__create_command_key_uninstall)

		h = _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT, 'Directory')
		self.__delete_key(h, self.__create_command_key_uninstall)
		
		print 'Done.'
