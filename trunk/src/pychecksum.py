#! /usr/bin/python
# -*- coding: iso-8859-15 -*-

from optparse import OptionParser
import os.path
import sys

def main(gladedir, platform_win32):
	if platform_win32:
		usage = """
\t%prog [-xv] [--md5|--sfv] -cFILE
\t%prog [-xv] [--md5|--sfv] [-oFILE] [-bPATH] file1 [file2] [-i PATH1]
\t%prog --register
\t%prog --unregister
\t%prog (-h|--help)"""
	else:
		usage = '%prog [-xvg] [--md5|--sfv] (-cFILE | [-oFILE] [-bPATH] file1 [file2] [-i PATH1])'
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
	parser.add_option("-v", action = "store_true", dest="verbose",
		help="print status on the console", default = False)
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
			ext_output = ".md5"
		else:
			sum = SfvFile()
			ext_output = ".sfv"
			
		if options.singlefile:
			# create sum for a single file
			basedir = os.path.dirname(options.singlefile)
			outfilename = options.singlefile + ext_output
			w = CreateWindow(options.expanded, options.interface, gladedir)
			w.show_all()
			idle_add(w.create_sum(sum, [options.singlefile], outfilename, None, basedir, options.verbose).next)
		
		elif options.singledir:
			# create sum for a single dir
			basedir = '.'
			options.singledir = options.singledir.rstrip("\\").rstrip("/").rstrip('"')
			outfilename = os.path.join(options.singledir, os.path.basename(options.singledir)) + ext_output
			try:
				os.remove(outfilename)
			except OSError:
				pass
			w = CreateWindow(options.expanded, options.interface, gladedir)
			w.show_all()
			idle_add(w.create_sum(sum, [options.singledir], outfilename, options.ignore_dirs, basedir, options.verbose).next)
		
		else:
			if len(args) == 0 and options.infilename == None:
				parser.error('use -cFILE or provide a list of files')

			# check files against an existing md5sum file
			if options.infilename:
				w = VerifyWindow(options.expanded, options.interface, gladedir)
				w.show_all()
				idle_add(w.verify_sum(sum, options.infilename, options.verbose).next)
			
			else:
				w = CreateWindow(options.expanded, options.interface, gladedir)
				w.show_all()
				if options.outfilename:
					try:
						os.remove(options.outfilename)
					except OSError:
						pass
				idle_add(w.create_sum(sum, args, options.outfilename, options.ignore_dirs, options.basedir, options.verbose).next)
		gtk.main()
	
if __name__ == '__main__':
	moduledir = os.path.abspath(os.path.dirname(__file__))
	platform_win32 = sys.platform.startswith("win")

	sys.path.append(moduledir)
	
	from Main import *
	from SumFile import *
	
	if platform_win32:
		import Register
		
	main(moduledir, platform_win32)
