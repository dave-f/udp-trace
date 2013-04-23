import sublime
import sublime_plugin
import socket
import threading
import datetime
import functools

quitEvent = threading.Event()

#
# Worker thread
class UdpTraceThread(threading.Thread):
	"""Simple thread to read data from a UDP port"""
	def __init__(self, theView, ipAddress, portNo, maxEntries):
		threading.Thread.__init__(self)
		self.theView = theView
		self.ipAddress = ipAddress
		self.portNo = portNo
		self.maxEntries = maxEntries

	def run(self):
		now = datetime.datetime.now()
		print "UDP trace thread starting at " + now.strftime("%d/%m/%Y %H:%M:%S")
		try:
			sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
			sock.settimeout(1.0)
			sock.bind((self.ipAddress,self.portNo))
			while (not quitEvent.is_set()):
				try:
					data,addr = sock.recvfrom(1024)
					sublime.set_timeout(functools.partial(self.update,data),0) # partial behaves like bind in c++
				except:
					# Ignore for now; probably just a socket timeout
					pass
		except:
			sublime.set_timeout(functools.partial(self.update,"Connection error."),0)
		now = datetime.datetime.now()
		print "UDP trace thread ending at " + now.strftime("%d/%m/%Y %H:%M:%S")

	def update(self, data):
		lines, _ = self.theView.rowcol(self.theView.size())
		e = self.theView.begin_edit()
		if ( lines >= self.maxEntries ):
			# Erase beginning
			pt = self.theView.text_point(0, 0)
			self.theView.erase(e,self.theView.full_line(pt))
		self.theView.insert(e,self.theView.size(),data)
		self.theView.insert(e,self.theView.size(),'\n')
		self.theView.end_edit(e)

#
# Simple UDP Trace command
class UdpTraceCommand(sublime_plugin.WindowCommand):
	"""Prints out data received over the network into a Sublime buffer"""
	def run(self):
		# Load our settings
		s = sublime.load_settings("udptrace.sublime-settings")
		ipAddress = s.get("address","127.0.0.1")
		portNo = s.get("port","1777")
		bufferMode = s.get("buffer_mode","Packages/Text/Plain text.tmLanguage")
		maxEntries = s.get("max_entries",100)
		ok = True
		for v in self.window.views():
			# Don't run if we are already
			if (v.name() == "*UDP Trace*"):
				ok = False
				break

		if (ok):
			v = self.window.new_file()
			v.set_name("*UDP Trace*")
			v.set_scratch(True)
			v.set_syntax_file(bufferMode)
			quitEvent.clear()
			t = UdpTraceThread(v, ipAddress, portNo, maxEntries)
			t.start()
		else:
			sublime.error_message("Already active")

class CloseListener(sublime_plugin.EventListener):
	def on_close(self, v):
		if (v.name() == "*UDP Trace*"):
			# Signal to thread
			quitEvent.set()
