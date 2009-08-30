#!/usr/bin/python
import time
infile=open("debian-501-i386-kde-CD-1.iso","rb")
prefix="splitfile"
ofilen=2
M=1024*1024
MC=10*M
_count=100
count=_count*M
iternum=count/MC
go=1			#
stime=time.time()
#"""
infile.seek(count*ofilen)
filename="/path/to/file/"+prefix+'%010'%ofilen
ofile=open(filename,"wb")
for i in xrange(0,iternum):  
	buf=infile.read(MC) 
	if not len(buf):
		print ofilen,"ended - quitting"
		go=0
		break

	ofile.write(buf)
ofile.close()
print "wrote",filename
print "went",float(_count)/(time.time()-stime),"MBPS over",time.time()-stime
stime=time.time()
#""""""
"""
while go:
	filename="/path/to/file/"+prefix+str(ofilen)
	ofile=open(filename,"wb")
	for i in xrange(0,iternum):  
		buf=infile.read(MC) 
		if not len(buf):
			print ofilen-100,"ended - quitting"
			go=0
			break
	
		ofile.write(buf)
	ofile.close()
	print "wrote",filename
	print "went",float(_count)/(time.time()-stime),"MBPS over",time.time()-stime
	stime=time.time()
	ofilen+=1
#"""

