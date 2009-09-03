#!/usr/bin/python
#TODO: make get work for inet, add push, fix space-in-share-path bug
import sys, getopt, os, commands, shutil

default_mdata_dir="~/.disknet"
#default_mdata_dir="./disknet"
M=1024*1024
MC=10*M
usage_messages="""Note that this will only run on Unix-based python installs right now."""
usage_global="""Global options:
    -h		--help		show this message
    -H		--help-all	show this message and all command help messages
    -s DIR	--sharedir=DIR	use DIR as share
    -d DIR	--diskdir=DIR	use DIR as disk. on wingdoze, this is D:\\ or 
    				 similar. on Linux and other unixes, this is the
    				 default mountpoint of the disk
    -p ADDR	--addr=ADDR	use ADDR as the disknet address of this computer
    				 <name>.<computername>
"""
usage_commands={
"commands":"""    
Commands:
	setup		set up and change the metadata on the local system
	showsetup	show the setup on the local system
	setupdisk	setup metadata on a disk
	sync		sync a disk - can take a long time as it does the copy
	get		que a file to be copied to this system on next sync that
			 makes it possible.
			 
Unimplemented but Coming Commands:
	browseindex	will list all indexes in the metadata
""",
"shared":"""Options shared between Commands:
    -h		--help		display help for command
    -m DIR	--metadir=DIR	read/write metadata from DIR. 
    				 defaults to '~/.disknet'
""",
"setup":"""
Setup Command Options:
    -s DIR	--sharedir=DIR	set DIR as default share in metadata
    -d DIR	--diskdir=DIR	set DIR as default dir in metadata
    -p ADDR	--addr=ADDR	set ADDR as disknet addr in metadata
""",
"showsetup":"""
Showsetup Command Options:
    -m DIR	--metadir=DIR	read metadata from DIR. as in other places,
				 defaults to '~/.disknet'
""",
"setupdisk":"""
Setupdisk Command Options:
    -m DIR	--metadir=DIR	 read metadata from DIR. as in other places,
    				  defaults to '~/.disknet'
    -d DIR	--diskdir=DIR	 write disk metadata to DIR/.disknet. defaults
    				  to current directory when not specified
    -f N	--maxfilesize=N  use N as the maximum single file size for 
    				  disknet to create on this disk
    -u N	--maxtotaluse=N  use N as the maximum amount of disk space that
    				  disknet can use on this disk. should be a
    				  at least a little less than the size of the
    				  disk.
    -p ADDR	--addr=ADDR	 set the disk's address to ADDR. this follows
    				  the form <DISKNET>.<UNIQUE_NAME>.
""",
"sync":"""
Sync Command Options:
    -m DIR	--metadir=DIR	read metadata from DIR. as in other places,
    				 defaults to '~/.disknet'
    -d DIR	--diskdir=DIR	use DIR as disk
    -s DIR	--sharedir=DIR	use DIR as share
    -p ADDR	--addr=ADDR	use ADDR as this system's disknet address
    -q		--quiet		don't output anything to the screen
""",
"get":"""
Get Command Options:
    ADDR/FILE			write a request for FILE from ADDR. FILE can't
    				 have directorys in it's path right now. this
    				 can be used multiple times to request multiple
    				 things.
"""}
usage_sizes="""
options that accept a size N can have suffixes - K for *1024, M for *1024*1024,
G for *1024*1024*1024, and T for 1024*1024*1024*1024. 
KB, MB, etc are not supported.
"""
def freediskspace(path):
	if sys.platform == "linux2":
		r=os.statvfs_result(os.statvfs(path))
		return r.f_bsize*r.f_bavail
	else:
		return 0 #could be a bad idea

def useddiskspace(path):
	return 0 # for testing purposes
	if sys.platform == "linux2":
		r=os.statvfs_result(os.statvfs(path))
		return r.f_bsize*r.f_blocks-r.f_bsize*r.f_bfree
	else:
		return 0 #could be a bad idea

def freedisknetspace(path,mdu):	#so that this calculation doesn't take up space in the small places it's used
	return max(mdu-useddiskspace(path),0)	#negative is unacceptable

def usage(progname,command=""):
	if command=="":
		print "Usage:",progname,"[GLOBAL_OPTION]... COMMAND [COMMAND_OPTION]..."
		print usage_messages
		print usage_global
		print usage_commands["commands"]
		print usage_commands["shared"]
	elif command=="all":
		print "Usage:",progname,"[GLOBAL_OPTION]... COMMAND [COMMAND_OPTION]..."
		print usage_messages
		print usage_global
		print usage_commands["commands"]
		print usage_commands["shared"]
		for i in ["setup","showsetup","setupdisk","sync","get"]:
			print usage_commands[i]
	else:
		print "Usage:",progname,"[GLOBAL_OPTION]... COMMAND [COMMAND_OPTION]..."
		print usage_commands["commands"]
		print usage_commands["shared"]
		print "-"*80
		print usage_commands[command]
		print "-"*80
def local_getopts(errexp,progname,argv,opts,longopts=[]):
	try:
		return getopt.gnu_getopt(argv,opts,longopts)
	except getopt.GetoptError, e:
		print errexp,e.msg
		print "Try '"+progname,"--help' for more information."
		sys.exit(126) 

def file2dict(filename,emptydict=0):
	try:
		f=open(filename)
		d={}
		for i in f.readlines():
			fields=i.split(" ")
			d[fields[0]]=" ".join(fields[1:])[:-1]
		f.close()
		return d
	except IOError, e:
		if e.errno==2 and emptydict:
			return {}
		else:
			raise

def dict2file(d,filename):
	l=d.items()
	#l.sort() #do we want this? not for now...
	if not os.path.exists(os.path.dirname(filename)):
		os.mkdir(os.path.dirname(filename))          #create one level of missing dir
	lines=[]
	for i in l:
		lines.append(" ".join((i[0],str(i[1])))+"\n")
	f=open(filename,"w")
	f.writelines(lines)
	f.close()
	
		
def fullpath(path):
	return os.path.realpath(os.path.expanduser(path))

def part(count,offset,infile,prefix,offsetisbytes=0):
	iternum=count/MC
	if iternum == 0:
		iternum = 1		#just a little failsafe - it might be triggered if count is a K number
	infile=open(infile,"rb") #convert the arg infile - a filename - into a real file ob
	if not offsetisbytes:
		offset*=count
	infile.seek(offset)
	filename=prefix
	if offsetisbytes:
		filename=filename+".disknet"	#it always will have this ... hmmm...
	else:
		filename=filename+'%010'%offset		#this will not work for byteoffsets
	if os.path.exists(filename):	#if it's still there, we dont want to overwrite it
		ofile=open(filename,"rb")
		infile.seek(0,2)
		lent=infile.tell()
		return offset, lent, filename
	ofile=open(filename,"wb")
	for i in xrange(0,iternum):  
		buf=infile.read(MC) 
		if not len(buf): # end of stream
			go=0
			break

		ofile.write(buf)
	cpos=infile.tell()
	infile.seek(0,2)
	lent=infile.tell()
	ofile.close()
	return cpos, lent, filename
	
def expandsize(size):
	if type(size) == type(""):
		try:
			s=int(size)
			print "WARNING: expandsize() was passed a bytecount!! use kilobytes or megabytes, or larger."
			return s
		except:
			pass		#not that simple, obviosly
		mult=size[-1]
		size=int(size[:-1])
		
		if mult=="K" or mult=="k":
			size*=1024
		elif mult=="M" or mult=="m":
			size*=1024*1024
		elif mult=="G" or mult=="g":
			size*=1024*1024*1024
		elif mult=="T" or mult=="t":	#gotta support it - people use it sometimes, goofballs
			size*=1024*1024*1024*1024	#and you just gotta hope that they have fast systems
		return int(size)
	else:
		print "WARNING: expandsize() was passed a bytecount!! use kilobytes or megabytes, or larger."
		return int(size) #for some reason someone's using bytes - not a good idea
		
def append(fromf,tof):
	fromf=open(fromf,"rb")
	tof=open(tof,"ab")
	tof.seek(0,2)
	while 1:
		buf=fromf.read(MC) 
		if not len(buf): # end of stream
			break
		tof.write(buf)
	fromf.close()
	tof.close()
		

def main():
	#from getopt import gnu_getopt as getopts
	
	from sys import argv
	progname=os.path.basename(argv[0])
	argv=argv[1:]
	opts=[]
		
	(opts,argv)=local_getopts(progname+":",progname,argv,"+hHs:d:p:",["help","diskdir=","sharedir=","addr=","help-all"])
	opts.sort()
	
	if ("--help","") in opts or ("-h","") in opts:
		usage(progname)
		sys.exit(0)
	if ("--help-all","") in opts or ("-H","") in opts:
		usage(progname,"all")
		sys.exit(0)	
	print
	command=argv[0]
	argv=argv[1:]
	if command=="get":
		(opts2,argv)=local_getopts(progname+": sync:",progname,argv,"hm:",["help","metadir="])
		opts.extend(opts2)
		if ("--help","") in opts or ("-h","") in opts:
			usage(progname,command)
			sys.exit(0)
		metadata_dir=os.path.expanduser(default_mdata_dir)
		for i in opts:
			if i[0]=="--metadir" or i[0]=="-m":
				metadata_dir=fullpath(i[1])
		rqfromme=file2dict(fullpath(metadata_dir+"/requests"),1)
		for request in argv:
			rqfromme[request]=1
		dict2file(rqfromme,fullpath(metadata_dir+"/requests"))
	elif command=="sync":
	
		(opts2,argv)=local_getopts(progname+": sync:",progname,argv,"hm:s:d:p:q",["help","metadir=","diskdir=","sharedir=","addr=","quiet"])
		opts.extend(opts2)
		if ("--help","") in opts or ("-h","") in opts:
			usage(progname,command)
			sys.exit(0)
		metadata_dir=os.path.expanduser(default_mdata_dir)
		diskdir="" #empty means "load from metadata"
		sharedir=""
		addr=""
		for i in opts:
			if i[0]=="--metadir" or i[0]=="-m":
				metadata_dir=fullpath(i[1])
			elif i[0]=="--diskdir" or i[0]=="-d":
				diskdir=fullpath(i[1])
			elif i[0]=="--sharedir" or i[0]=="-s":
				sharedir=fullpath(i[1])
			elif i[0]=="--addr" or i[0]=="-p":
				addr=i[1]
				
		meta_settings=file2dict(metadata_dir+"/settings")
		
		if "diskdir" in meta_settings and diskdir=="":
			diskdir=fullpath(meta_settings["diskdir"])
			
		if "sharedir" in meta_settings and sharedir=="":
			sharedir=fullpath(meta_settings["sharedir"])
			
		if addr != "":
			pass
		elif "addr" in meta_settings:
			addr=meta_settings["addr"]
		else:
			print progname+": sync: no ip specified in config file or on command line!\nplease run '"+progname,"setup --addr=<IP>'"
		print "sync:"
		print "metadatadir:",fullpath(metadata_dir)
		print "diskdir:",fullpath(diskdir)
		print "sharedir:",fullpath(sharedir)
		print "addr:",addr
		
		#what do we have to do to sync? verify the disk is a disknet disk,
		#parse incoming requests then fulfill them,
		#parse outgoing requests and copy any available files,
		#copy and make indexes 
		
		
		#1. verify disk
		failquiet=0
		if ('-q','') in opts:
			failquiet=1
		def fail(num): #we reuse this code a lot in the next few ifs
			if failquiet:
				sys.exit(0)
			elif num==1:
				print progname+": sync: disk is not a disknet-enabled disk."
				print "use '"+progname+" setupdisk' to make it one."
				sys.exit(10)
			elif num==2:
				print progname+": sync: disk is a disknet-enabled disk, but for a different disknet."
				print "use '"+progname+" setupdisk' to make it work for this one."
				sys.exit(10)
		for i in ['/.disknet/','/.disknet/settings','/.disknet/requests','/.disknet/partials','/.disknet/indexes']:
			if not os.path.exists(fullpath(diskdir+i)):
				fail(1)
		disksettings=file2dict(fullpath(diskdir+"/.disknet/settings"))
		diskcnet='.'.join(disksettings["addr"].split('.')[:-1])
		cnet='.'.join(meta_settings["addr"].split('.')[:-1])
		if cnet!=diskcnet:
			fail(2)
		print "disk passed"
		requests=file2dict(fullpath(diskdir+"/.disknet/requests"))
		partials=file2dict(fullpath(diskdir+"/.disknet/partials"))
		print "opened requests, partials"
		#copy and make indexes:
		#1. make...
		index=file2dict(fullpath(diskdir+"/.disknet/indexes"))
		index[meta_settings["addr"]]=repr(commands.getoutput("find "+fullpath(sharedir)+" -type f -exec ls -sh {} \;"))
		#update out entry
		#then save
		dict2file(index,fullpath(diskdir+"/.disknet/indexes"))
		print "indexes created,",
		
		#copy index file to our metadata dir
		shutil.copyfile(fullpath(diskdir+"/.disknet/indexes"),fullpath(metadata_dir+"/indexes"))
		print "copied"
		
		#copy requests that have been fulfilled for us
		rqfromme=file2dict(fullpath(metadata_dir+"/requests"),1)
		afterdel=[]
		print "copying any fulfilled requests"
		for i in rqfromme:
			print "\trequest:",i
			raddr=i.split('/')[0]
			path='/'.join(i.split('/')[1:])	#it should just be addr/file, but it may be addr/dir/to/file - which will probably break at the moment
			req_host_partials=eval(partials.get(raddr,"{}"))
			req_host_requests=eval(requests.get(raddr,"{}"))
			if os.path.exists(fullpath(diskdir+"/"+path+".disknet")): #it's been copied
				print "\tfile available, copying"
				append(fullpath(diskdir+"/"+path+".disknet"),fullpath(sharedir+"/"+path))	#copy onto ours
				print "\tcopied",
				if  path in req_host_requests:	# it should be
					print "\trequest remains"
					if not path in req_host_partials:
						print "\tno partials"
						if addr in req_host_requests[path]:
							print "\tdeleting out entry from server request list"
							del req_host_requests[path][addr]
							afterdel.append(i)
						if len(req_host_requests[path]) == 0:
							print "\tno client remain in request, deleting request"
							del req_host_requests[path]
					else:
						print "\tpartial!"
						if addr in req_host_requests[path]:
							print "\tupdating our entry in server request list"
							req_host_requests[path][addr]=req_host_partials[path]
						res=1
						print "\tchecking for clients behind us"
						for i in req_host_requests[path].items():
							if i[1]<req_host_partials[path]:
								res=0
						if res:
							print "\twe are the farthest client back, deleting file on disk"
							os.unlink(fullpath(diskdir+"/"+path+".disknet"))	#delete the file
						else:
							print "\tsome clients need to catch up, not deleting"
			else:	#it hasn't been copied yet, we need to check to see if the disk knows we want it.
				print "\tfile not available"
				if path in req_host_requests:	#this won't work if a partial exists for this path...
					print "\tfile has already been requested",
					if addr in req_host_requests[path]:
						print "by us"
						res=1
						for i in req_host_requests[path].items():
							if i[1]>req_host_requests[path][addr]:
								print "\tbut we got behind somehow! this is bad!!",
								res=0
						if not res: continue
					else:
						print "not by us, this is bad!"	#of course we want a better message - "copy in progress for other systems already"?
				else:	#we're the only asker right now
					print "no requests yet, adding request"
					req_host_requests[path]={addr:0}
			requests[raddr]=req_host_requests
		for i in afterdel:
			del rqfromme[i]	
				
		#parse / fulfill requests
		rqtome=eval(requests.get(addr,"{}"))	#cheat off of python's parsing
		prtome=eval(partials.get(addr,"{}"))	#partials need to hold the partial byte too
		print "fulfilling requests"
		for i in rqtome:	#this won't work so well if mfs is set too large
			print "\trequest to us:",i
			continuespot=0
			if i in prtome: 
				print "\tpartial exists"
				continuespot=prtome[i]
			mdu_avail=freedisknetspace(diskdir,expandsize(disksettings["mdu"]))
			print "\tmdu_avail:",mdu_avail
			if not mdu_avail:
				break
			print "\tparting"
			(a,b,c)=part(		#dont use c here, but we need to get rid of the third value
						min(
								expandsize(disksettings["mfs"]),
								mdu_avail
							),
						continuespot,
						fullpath(sharedir+"/"+i),
						fullpath(diskdir+"/"+i),
						1) 
			print "\t\tparted"
			if a==b:		#a problem with this partial system is that when multiple computers want the same largefile, they might get out of sync.
				print "\tfile complete, removing parial if any"
				if prtome.has_key(i):
					del prtome[i]	#update the partial
			else:
				print "\tfile incomplete, setting partial"
				prtome[i]=a
		print "finished fulfilling"
		partials[addr]=prtome
		requests[addr]=rqtome
		print "saving dicts"
		dict2file(partials,fullpath(diskdir+"/.disknet/partials"))
		dict2file(requests,fullpath(diskdir+"/.disknet/requests"))
		dict2file(rqfromme,fullpath(metadata_dir+"/requests"))
		#-----------------------------------------------------------------------
		#_______________________________________________________________________
	elif command=="setup": #this is designed to be run both for initial setup and for changing the setup
	
		(opts2,argv)=local_getopts(progname+": setup:",progname,argv,"hm:s:d:p:",["help","metadir=","diskdir=","sharedir=","addr="])
		opts.extend(opts2)
		if ("--help","") in opts or ("-h","") in opts:
			usage(progname,command)
			sys.exit(0)
		metadata_dir=os.path.expanduser(default_mdata_dir)
		for i in opts:
			if i[0]=="--metadir" or i[0]=="-m":
				metadata_dir=fullpath(i[1])
		meta_settings=file2dict(metadata_dir+"/settings",1)
		for i in opts:
			if i[0]=="--diskdir" or i[0]=="-d":
				meta_settings["diskdir"]=os.path.realpath(i[1])
			elif i[0]=="--sharedir" or i[0]=="-s":
				meta_settings["sharedir"]=os.path.realpath(i[1])
			elif i[0]=="--addr" or i[0]=="-p":
				meta_settings["addr"]=i[1]
		dict2file(meta_settings,metadata_dir+"/settings")
		for i in meta_settings.items():
			print i[0]+"="+i[1]
		print 
		print "metadatadir="+metadata_dir
	elif command=="showsetup":
		(opts2,argv)=local_getopts(progname+": showsetup:",progname,argv,"hm:",["help","metadir="])
		opts.extend(opts2)
		if ("--help","") in opts or ("-h","") in opts:
			usage(progname,command)
			sys.exit(0)
		metadata_dir=os.path.expanduser(default_mdata_dir)
		for i in opts:
			if i[0]=="--metadir" or i[0]=="-m":
				metadata_dir=fullpath(i[1])
		meta_settings=file2dict(metadata_dir+"/settings",1)
		for i in meta_settings.items():
			print i[0]+"="+i[1]
	elif command=="setupdisk": #this is initial setup only - should be all that's necessary
		(opts2,argv)=local_getopts(progname+": setupdisk:",progname,argv,"hm:d:f:u:p:",["help","metadir=","diskdir=","maxfilesize=","maxtotaluse=","addr="])
		opts.extend(opts2)
		if ("--help","") in opts or ("-h","") in opts:
			usage(progname,command)
			sys.exit(0)
		metadata_dir=os.path.expanduser(default_mdata_dir)
		diskdir=""
		for i in opts:
			if i[0]=="--diskdir" or i[0]=="-d":
				diskdir=fullpath(i[1])
		"""
		if diskdir=="":
			for i in opts:
				if i[0]=="--metadir" or i[0]=="-m":
					metadata_dir=fullpath(i[1])
			meta_settings=file2dict(metadata_dir+"/settings",1)
			diskdir=meta_settings["diskdir"]
		"""  # we wouldn't want to use the metadata to find a disk if we're doing it manually would we?
		if diskdir=="":
			diskdir=fullpath(".")
		addr=""
		mdu=""
		mfs=""
		for i in opts:
			if i[0]=="--maxtotaluse" or i[0]=="-u":
				mdu=i[1]
			if i[0]=="--maxfilesize" or i[0]=="-f":	
				mfs=i[1]
			if i[0]=="--addr" or i[0]=="-p":
				addr=i[1]
		if mfs=="":
			print progname+": setupdisk: missing maximum file size argument"
			print "Try '"+progname,"--help' for more information."
			sys.exit(12)
		if mdu=="":
			print progname+": setupdisk: missing maximum disk usage argument"
			print "Try '"+progname,"--help' for more information."
			sys.exit(12)
		if addr=="":
			print progname+": setupdisk: missing disk address argument"
			print "Try '"+progname,"--help' for more information."
			sys.exit(12)
		dict2file({"addr":addr,"mfs":mfs,"mdu":mdu},diskdir+"/.disknet/settings")
		open(diskdir+"/.disknet/requests","a").close() #touch
		open(diskdir+"/.disknet/partials","a").close()
		open(diskdir+"/.disknet/indexes","a").close()
	else:
		print progname+":",command+": no such command.\nif it's in the unimplemented list, however, then it's coming!"
		print "Try '"+progname,"--help' for more information."
#END OF MAIN
main()		#comment this to use as a module
