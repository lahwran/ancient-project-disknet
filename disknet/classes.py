#!/usr/bin/python
class request:
	substitutions={
		"type":{
			"get":"get",
			"push":"push",
			"pull":"get",
			"send":"push",
			"wget":"inet",
			"inet":"inet",
			"www":"inet"
			},
		"end":{
			"requester":"requester",
			"requestee":"requestee"	#useful to cause a keyerror for things we don't know about
			}
		#,""
		}
	def __init__(self,initstr):
		initstr=initstr.split(" ")
		try:
			self.type=substitutions["type"][initstr[0]]	#get, push, inet, others are error
		except KeyError:
			return "no such request type:",initstr[0]
		try:
			self.end=initstr[1]	#which end are we on - server or client?
		except KeyError:
			return "no such end type:",initstr[0]
		if self.end=="requester":
			if self.type=="get":
				#get setup
			elif self.type=="push":
				#push setup
			elif self.type=="inet":
				#inet setup
		else:	#effectivly no way to get anything other than "requester" or "requestee"
			
		
