#! /usr/bin/python
# -*- coding: iso-8859-15 -*-

import _winreg
import os
import sys

CONTEXT_MENU_CHECK = 'Verify'
CONTEXT_MENU_CREATE = 'Generate MD5 sum'

MD5_EXTENSION = '.md5'
MD5_ICON = 'shell32.dll,104'
MD5_INFO = 'md5 sum'

REGISTRY_CHECK_KEY = 'md5file'
REGISTRY_CHECK_COMMAND_KEY = 'shell\\%s\\command' % CONTEXT_MENU_CHECK

REGISTRY_CREATE_COMMAND_KEY_UNINSTALL = 'shell\\%s' % CONTEXT_MENU_CREATE
REGISTRY_CREATE_COMMAND_KEY = 'shell\\%s\\command' % CONTEXT_MENU_CREATE

def update_constants(script):
	global REGISTRY_CHECK_COMMAND
	global REGISTRY_CREATE_COMMAND_FILE
	global REGISTRY_CREATE_COMMAND_DIRECTORY

	REGISTRY_CHECK_COMMAND = '%s\\pythonw.exe  "%s" -c "%%1"' % (sys.exec_prefix, script)
	REGISTRY_CREATE_COMMAND_FILE = '%s\\pythonw.exe "%s" -f "%%1"' % (sys.exec_prefix, script)
	REGISTRY_CREATE_COMMAND_DIRECTORY = '%s\\pythonw.exe "%s" -d "%%1"' % (sys.exec_prefix, script)
	
def register(script):
	update_constants(script)
	print "Registering ...",

	h = _winreg.CreateKey(_winreg.HKEY_CLASSES_ROOT, MD5_EXTENSION)
	_winreg.SetValueEx(h, None, 0, _winreg.REG_SZ, REGISTRY_CHECK_KEY)

	h = _winreg.CreateKey(_winreg.HKEY_CLASSES_ROOT, REGISTRY_CHECK_KEY)
	_winreg.SetValueEx(h, None, 0, _winreg.REG_SZ, MD5_INFO)

	h1 = _winreg.CreateKey(h, 'DefaultIcon')
	_winreg.SetValueEx(h1, None, 0, _winreg.REG_SZ, MD5_ICON)

	h1 = _winreg.CreateKey(h, REGISTRY_CHECK_COMMAND_KEY)
	_winreg.SetValueEx(h1, None, 0, _winreg.REG_SZ, REGISTRY_CHECK_COMMAND)

	# write the handler for single files
	h = _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT, '*')
	h = _winreg.CreateKey(h, REGISTRY_CREATE_COMMAND_KEY)
	_winreg.SetValueEx(h, None, 0, _winreg.REG_SZ, REGISTRY_CREATE_COMMAND_FILE)

	# write the handler for directories
	h = _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT, 'Directory')
	h = _winreg.CreateKey(h, REGISTRY_CREATE_COMMAND_KEY)
	_winreg.SetValueEx(h, None, 0, _winreg.REG_SZ, REGISTRY_CREATE_COMMAND_DIRECTORY)

	print 'Done.'

def delete_key(base_key, sub_key):
    try:
        key = _winreg.OpenKey(base_key, sub_key)
        while True:
            # delete subkeys of the sub_key
            try:
                while True:
                    delete_key(key, _winreg.EnumKey(key, 0))
            except EnvironmentError:
                break
        _winreg.DeleteKey(base_key, sub_key)
    except EnvironmentError:
        pass

def unregister():
	print "Unregistering ...",
	delete_key(_winreg.HKEY_CLASSES_ROOT, MD5_EXTENSION)
	delete_key(_winreg.HKEY_CLASSES_ROOT, REGISTRY_CHECK_KEY)

	h = _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT, '*')
	delete_key(h, REGISTRY_CREATE_COMMAND_KEY_UNINSTALL)

	h = _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT, 'Directory')
	delete_key(h, REGISTRY_CREATE_COMMAND_KEY_UNINSTALL)
	
	print 'Done.'
