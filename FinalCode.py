import networkx as nx
from sys import exit
import os
import requests
#import json
import simplejson as json
import unicodedata
from subprocess import Popen, PIPE
import time


def deviceInformation(data):
    global deviceMAC
    global switch
    switchDPID = ""
    global hostPorts
    
    for i in data:
        x = i['ipv4']
        if(x):
            #ip = i['ipv4'][0].encode( 'ascii' , 'ignore' )
            ip = i['ipv4'][0]
            #print(ip)
            mac = i['mac'][0].encode( 'ascii' , 'ignore' )
            deviceMAC[ip] =mac
            #print("----")
            y = i['attachmentPoint']
            for j in y:
                if 'switchDPID' in j.keys():
                    switchDPID=j['switchDPID']
                    switch[str(ip)]=switchDPID
                else:
                    portNumber=j[key]
                    hostPorts[ ip +"::"+ switchDPID.split( ":" )[7]] = str(portNumber)


def fetchResp(url,choice):
    response = requests.get(url)

    if(response.ok):
        jData = json.loads(response.content.decode('utf-8'))
        if (choice == "deviceInfo" ):
            deviceInformation(jData)
        elif (choice == "getswitchlatency"):
            getswitchlatency(jData)
        elif (choice == "costcompute"):
            costcompute(jData,portKey)
        elif (choice == "Switchlinkinfo"):
            #print(switch)
            Switchlinkinfo(jData,switch[h2])
        
    else:
        #response.raise_for_status()
        #print("abc")
        return

def Switchlinkinfo(data,s):
        
    global G
    global switchLinks
    global linkPorts

    links =[]
    for i in data:
        source , destination = i['src-switch'] , i['dst-switch']
        sourcePort , destinationPort = str( i['src-port'] ) , str(i['dst-port'])
        sourceTemp , destinationTemp = source.split(":")[7] , destination.split(":")[7]
         
        try:
            latency = str(i['latency'])
        except Exception as e:
            latency ="0"

        G.add_edge( int(sourceTemp , 16), int(destinationTemp , 16))            

        linkPorts[sourceTemp +"::"+ destinationTemp] = str(sourcePort) +"::"+ str(destinationPort)
        linkPorts[destinationTemp +"::"+ sourceTemp] = str(destinationPort) +"::"+ str(sourcePort)

        linklat[sourceTemp +"::"+ destinationTemp] = latency
        linklat[destinationTemp +"::"+ sourceTemp] = latency
                
        if(source == s):
            links.append( destination )
        elif(destination == s):
            links.append( source )
        else:
            continue
        
    switchLinks[s.split(":")[7]] = links
        

#Cost computation for all links
def costcompute(data,key):
    global cost
    port = linkPorts[key].split("::")[0]
    for i in data:
        if i['port']==port:
            xx = i['bits-per-second-tx']
            cost = cost + (int)( xx )
                       
        

def computeRoute():
    
    nodeList = []
    a1 =  switch[h2]
    a2 = switch[h1]
    src = int( a1.split(":", 7 )[7],16)
    dst = int( a2.split(":", 7 )[7],16)
    #print ("source is:",src)
    #print ("destination is:",dst)
    pathKey = ""

    for currentPath in nx.all_shortest_paths(G,source = src,target = dst,weight = None):
        for node in currentPath:

            tmp=""
            a = str(hex(node)).split( "x" , 1)[1]
            if node>=17:                
                pathKey = pathKey+a +"::"
                tmp = "00:00:00:00:00:00:00:" +a
              
            else:
                pathKey = pathKey +"0"+a+"::"
                tmp = "00:00:00:00:00:00:00:0"+a

            nodeList.append(tmp)
            #print(tmp)
            #print("##################")
        path[pathKey.strip("::")] = nodeList
        pathKey = ""
        nodeList = []


def fetchLinkCost():
    global portKey
    global cost
    global finalcost
    
    for key in path:           
        start = switch[h2]
        src = start
               
        srcShortID = src.split( ":" )[7]
        mid = path[key][1].split( ":" )[7]
        xx = path[key]

        for link in xx:
            temp = link.split(":")[7]
                        
            if srcShortID == temp:
                continue
            else:
                portNumber = linkPorts [srcShortID+ "::" +temp].split( "::" )[0]
                stats = "http://localhost:8080/wm/statistics/bandwidth/" + src +  "/" + portNumber + "/json"
                a = "costcompute"
                fetchResp(stats,a)
                srcShortID=temp
                src=link
        a1 = start.split(":")[7]
        a2 = switch[h1].split( ":" )[7]
        finalcost[ a1 + "::"+mid+"::"+a2 ]=cost
        cost=0


def flowRule( currentNode ,flowCount ,inPort ,outPort ,staticFlowURL):
    a=False
    b="true"
    xx = "00:00:00:00:00:00:00:"
    ff = "flow" + str(flowCount)
    zero = "0"
    max_pr = "32768"
    eth_type = "0x0800"
    flow = {
        'switch': xx+currentNode,
        "name" : ff,
        "cookie" : zero,
        "priority" : max_pr,
        "in_port" : inPort,
        "eth_type" : eth_type,
        "ipv4_src" : h2,
        "ipv4_dst" : h1,
        "eth_src" : deviceMAC[h2],
        "eth_dst" : deviceMAC[h1],
        "active" : b,
        "actions" : "output="+outPort
    }

    cmd = "curl -X POST -d \'"+json.dumps(flow) +"\' "+staticFlowURL

    while(a):
        print(flow)

    systemCommand(cmd)
    flowCount = 1 + flowCount

    xx = "00:00:00:00:00:00:00:"
    ff = "flow" + str(flowCount)
    zero = "0"
    max_pr = "32768"
    
    flow = 
    {
        'switch' :  xx+ currentNode,
        "name" : ff,
        "cookie" : zero,
        "priority" : max_pr,
        "in_port" : outPort,
        "eth_type" :eth_type,
        "ipv4_src" : h1,
        "ipv4_dst" : h2,
        "eth_src" : deviceMAC[ h1 ],
        "eth_dst" : deviceMAC[ h2 ],
        "active" : b,
        "actions" : "output=" + inPort
    }
    cmd = "curl -X POST -d \'" + json.dumps(flow) + "\' " + staticFlowURL
    systemCommand(cmd)


def systemCommand(cmd):
    terminalProcess = Popen(cmd,stdout = PIPE ,stderr = PIPE,shell = True)
    terminalOutput, stderr = terminalProcess.communicate()


def RR(c, arr):
    n = c % 2
    return arr[n]


def addFlow():
    global bestPath
    global shortestPath
    
    flowCount = 1

    shortestPath = min(finalcost, key = finalcost.get)
    

    
    while(False):
        print("1")
    # Port Computation
    nextNode = shortestPath.split("::")[1]
    currentNode = shortestPath.split( "::" , 2)[0]
    port = linkPorts[currentNode + "::" + nextNode]
    outPort = port.split("::")[0]
    
    try:
        inPort = hostPorts[ h2 + "::" + switch[h2].split(":")[7] ]
    except Exception as e:
        inPort = port.split( "::" )[1]

    flowRule(currentNode ,flowCount,inPort,outPort, "http://127.0.0.1:8080/wm/staticflowpusher/json")
    previousNode = currentNode
    flowCount= 2 +flowCount
    bestPath = path[shortestPath]
    l = len(bestPath)

    for currentNode in range(0,l):
        if previousNode == bestPath[currentNode].split(":")[7]:
            continue
        else:
            aa = bestPath[ currentNode ].split(":")[7] +"::"+previousNode
            inPort = linkPorts[aa].split("::")[0]
            outPort = ""
            while(False):
                print("1")
    
            if( currentNode<len(bestPath)-1 and bestPath[currentNode]==bestPath[currentNode + 1]):
                currentNode=currentNode + 1
                continue
            
            elif(bestPath[ currentNode ]==bestPath[-1] ):
                xx = h1 + "::" + switch[h1].split( ":" )[7] 
                aa = hostPorts[ xx ]
                outPort = str(aa)

            elif( currentNode < len(bestPath) -1 ):
                xx1 = linkPorts[ bestPath[ currentNode ].split( ":" )[7]
                xx2 = bestPath[currentNode+1].split( ":" )[7]]
                port = xx1 + "::"+ xx2
                outPort = port.split("::")[0]
            a1 = bestPath[currentNode].split( ":" )[7]
            flowRule(a1,flowCount, str(inPort) ,str(outPort), "http://127.0.0.1:8080/wm/staticflowpusher/json")
            flowCount =flowCount + 2
            previousNode =a1
        return bestPath


def statcolect(self, element):
        #print "Self values"
        #print "*********" 
        l = 0
        self.count +=1
        self.ipList.append(element)
        if self.count == 50:
            for i in self.ipList:
                l +=1
                if i not in self.entDic:
                    self.entDic[i] =0
                self.entDic[i] +=1
            self.entropy(self.entDic)
            #log.info(self.entDic)
            self.entDic = {​​​​​​​​}​​​​​​​​​​​​​​​
            self.ipList = []
            l = 0
            self.count = 0


def Random(arr):
    n = random.randint(0,1)
    return arr[n]


def getlinkLatency():
    global pathlat
    global linklat
    a = False
    for key in pathlat:
        length = len(key.split('::'))
        count=1
        while(a):
            print(key)
        for i in key.split('::'):
            temp2 = i + '::' + key.split('::')[count]
            pathlat[key] = int(pathlat[key]) + int(linklat[temp2]) 
            count = count + 1
            if length == count:
               break    
   

def getswitchlatency(jData):
    global temp
    global pathlat
    global path
    
    temp=0
    for key in path:
        path_key = path[key]
        for switch in path_key:
            print(switch)
            try:
                duration = int( switch.split( ':' ) [ -1])
                bytecount = int( switch.split( ':' )[ -1])
            except Exception as e:
                duration = 2
                bytecount = 2
            if( bytecount==0 ) : bytecount = 1
            temp += ( duration / bytecount) * 100
        pathlat[ key ] = temp
        temp = 0
    

def loadbalance():
    #Method to get data 
    fetchResp("http://localhost:8080/wm/topology/links/json" , "Switchlinkinfo")
    #Finding best Route for Traversal from host to destination 
    computeRoute()

    url = ('http://localhost:8080/wm/core/switch/all/flow/json')
    #Finding best Route for Traversal from host to destination 
    fetchResp(url , "getswitchlatency")

    getlinkLatency()
    #Find link cost from bandwidth URI
    fetchLinkCost()
    #Flow addition based on cost computation
    addFlow()


global h1,h2,h3

h1 = ""
h2 = ""
print()
print()
print("*********************Enter SOURCE and DESTINATION Hosts on which you want to do LOAD BALANCING*************************")
print()
print()
print("Enter SOURCE Host:")
h1 = int(input())
print()
print()
print("Enter DESTINATION Host: ")
h2 = int(input())
                  
path = {}
switchLinks = {}

h1 = "10.0.0." + str(h1)
h2 = "10.0.0." + str(h2)

deviceMAC = {}
finalcost = {}
pathlat = {}
linklat={}

hostPorts = {}
portKey = ""
cost = 0

switch = {}           
linkPorts = {}
G = nx.Graph()

try:

    requests.put("http://localhost:8080/wm/statistics/config/enable/json/")  
    fetchResp("http://localhost:8080/wm/device/","deviceInfo")
    #calling load balance function
    loadbalance()

    os.system('clear')
    
    print("\t")          
    print()
    print()
    print("######################FINAL OUTPUT#######################")
    print()
    print()

    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~Switch connected to HOST 1~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n\t\t\t\t\t", switch[h1])
    print()
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~IP and Mac addresses of all Devices in Topology~~~~~~~~~~~~~~~~~~\n\n", deviceMAC)

    # Host Switch Ports
    print()
    print()
    print("~~~~~~~~~~~~~~~~~~~~~Hosts and connected SwitchPorts~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n\n", hostPorts)
    print()
    print()
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~FINAL LINK COSTS~~~~~~~~~~~~~~~~~~~~~~~~~\n\t\t\t\t",finalcost)
    print()
    print()
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~Available Paths for routing~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n",path)
    print()
    print()
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~SHORTEST PATH for routing~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n\t\t\t\t\t\t ",shortestPath)
    print()
    print()
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~Best path for routing~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n\t\t\t",bestPath)
    print()
    print()
    print("~~~~~~~~~~~~~~~~~~~~~~~~LATENCY~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n\t\t\t\t",pathlat)

except KeyboardInterrupt:
    exit()
