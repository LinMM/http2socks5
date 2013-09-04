#coding:utf-8
'''
Created on 2013-9-4

@author: lingshao.zzy
一个httpserver+socks5client 的转换器   
http server from https://code.google.com/p/python-proxy/source/browse/trunk/PythonProxy.py
socks5 是自己写的
'''
import socket, thread, select,sys,struct

__version__ = '0.1.0 Draft 1'
BUFLEN = 8192
VERSION = 'Python Proxy/'+__version__
HTTPVER = 'HTTP/1.1'

class ConnectionHandler:
    def __init__(self, connection, address, timeout,socksserver=None,socksport=None):
        self.client = connection
        self.client_buffer = ''
        self.timeout = timeout
        self.socks5_server_ip=socksserver 
        self.socks5_server_port=socksport
        self.socks5_family=socket.AF_INET
        try:
            
            self.method, self.path, self.protocol = self.get_base_header()
            self._connect_target()
            if self.method=='CONNECT':
                self.method_CONNECT()
            elif self.method in ('OPTIONS', 'GET', 'HEAD', 'POST', 'PUT',
                             'DELETE', 'TRACE'):
                self.method_others()
            self.client.close()
            self.target.close()
        except :
            sys.exit()
    def get_base_header(self):
        i = 0
        while i < self.timeout:
            self.client_buffer += self.client.recv(BUFLEN)
            end = self.client_buffer.find('\n')
            if end!=-1:
                break
            i=i+1
        if i == self.timeout:
            raise Exception()
        #debug print '%s'%self.client_buffer[:end]
        data = (self.client_buffer[:end+1]).split()
        self.client_buffer = self.client_buffer[end+1:]
        return data

    def method_CONNECT(self):       
        self.client.send(HTTPVER+' 200 Connection established\n'+
                         'Proxy-agent: %s\n\n' \
                         %'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36')
        self.client_buffer = ''
        self._read_write()        

    def method_others(self):
        self.target.send('%s %s %s\n'%(self.method, self.path, self.protocol)+
                         self.client_buffer)
        self.client_buffer = ''
        self._read_write()

    #inject socks5 client
    def _connect_target(self):
        remote_host=self.path
        i = remote_host.find('://')
        remote_host=remote_host[i+3:]
        i=remote_host.find('/')
        remote_host=remote_host[:i]
        i=remote_host.find(':')
        if i!=-1:
            remote_host=remote_host[:i]
            remote_port=int(remote_host[i+1:])
        else:
            remote_port=80
        #使用socks5    
        if self.socks5_server_ip:   
            self.target = socket.socket(self.socks5_family)
            self.target.connect((self.socks5_server_ip,self.socks5_server_port))
            self.target.send(b'\x05\x01\x00')
            self.target.recv(2)
            message=b'\x05\x01\x00\x03'           
            remote_host_len=struct.pack('i',len(remote_host))[0]
            remote_port=struct.pack('!H',remote_port)
            self.target.send(message+remote_host_len+remote_host+remote_port)
            self.target.recv(10)
        #直接走http
        else:
            (soc_family, _, _, _, address) = socket.getaddrinfo(remote_host, remote_port)[0]
            self.target = socket.socket(soc_family)
            self.target.connect(address)
    def _read_write(self):
        time_out_max = self.timeout/3
        socs = [self.client, self.target]
        count = 0
        while 1:
            count += 1
            (recv, _, error) = select.select(socs, [], socs, 3)
            if error:
                break
            if recv:
                for in_ in recv:
                    data = in_.recv(BUFLEN)
                    if in_ is self.client:
                        out = self.target
                    else:
                        out = self.client
                    if data:
                        out.send(data)
                        count = 0
            if count == time_out_max:
                break

def start_server(host='localhost', port=8888, IPv6=False, timeout=60,
                 socksserver=None,socksport=None,
                  handler=ConnectionHandler):
    if IPv6==True:
        soc_type=socket.AF_INET6
    else:
        soc_type=socket.AF_INET
    soc = socket.socket(soc_type)
    soc.bind((host, port))
    #debug print "Serving on %s:%d."%(host, port)
    soc.listen(5)
    while 1:
        thread.start_new_thread(handler, soc.accept()+(timeout,socksserver,socksport))

if __name__ == '__main__':
    start_server()