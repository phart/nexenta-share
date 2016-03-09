#!/usr/bin/python
import urllib2 as u
import getopt
import json
import sys
import re

# port = 2004
port = 8457
server = '127.0.0.1'


def usage(exitcode):
    print 'USAGE: share.py [-n | -c sharename] [-s server] [-P port] [-e encoded_cred] [-B] [-u user] [-p password] foldername [quota]'
    print "\t-n is an NFS share, -c is a CIFS share"
    print "\tsharename is the string value you want for the CIFS share name"
    print "\tserver is the name or IP of a NexentaStor head; default is localhost"
    print "\tport is the port number for that head; default is 8457"
    print "\tencoded_cred is a base64 encoding of user:password"
    print "\t-B prints the base64 encoding of the provided user and password strings"
    print "\tuser is a username; default is 'admin'"
    print "\tpassword is the password for user for encoding"
    print "\tfoldername is path, e.g. volume/folder/subfolder"
    print "\tquota is quota value, either a number and a letter (e.g. 10G) or the word 'none'; defaults to none"
    sys.exit(exitcode)


def nza_rest(objtype='zvol', objmethod='get_names', params=['']):
    data = json.dumps({'object': objtype, 'method': objmethod, 'params': params})

    r = u.Request(url, data, headers)
    resp = u.urlopen(r)

    response = json.loads(resp.read())

    if not response['error']:
        return response
    else:
        # necessary to prevent confusion over different result types
        print "\nFailed\n"
        print response['error']['message']
        sys.exit(1)


#################################
#################################
def main():
    global url
    global server
    global port
    global headers

    nfs = False
    cifs = False
    path = None
    quota = 'none'
    show_encoding = False
    enc = False
    user = ''
    password = ''
    svcname = None
    quotaonly = False

    # Parse command line arguments
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hnc:s:P:Be:u:p:",
                                   ["help", "nfs", "cifs", "server", "port", "base64",
                                    "encoded_cred", "user", "password"])
    except getopt.GetoptError, err:
        print str(err)
        usage(2)

    for o, a in opts:
        if o in ("-h", "--help"):
            usage(0)
        elif o in ("-B", "--base64"):
            show_encoding = True
        elif o in ("-u", "--user"):
            user = a
        elif o in ("-p", "--password"):
            password = a
        elif o in ("-e", "--encoded_cred"):
            enc = True
            encoded_cred = a
        elif o in ("-n", "--nfs"):
            nfs = True
            svcname = 'svc:/network/nfs/server:default'
        elif o in ("-c", "--cifs"):
            cifs = True
            svcname = 'svc:/network/smb/server:default'
            sharename = a
        elif o in ("-s", "--server"):
            server = a
        elif o in ("-P", "--port"):
            port = a

    if (enc and show_encoding):
        print "\n-e and -B options are mutually exclusive\n"
        usage(1)

    if (enc and (user != '' or password != '')):
        print "\n-e and user/password values are mutually exclusive\n"
        usage(1)

    if (show_encoding and (user == '' or password == '')):
        print "\n-B option requires both user and password values\n"
        usage(1)

    if (show_encoding):
        cred = '%s:%s' % (user, password)
        print cred.encode('base64')[:-1]
        sys.exit()

    if (user == '' and password == ''):     # use defaults
        user = 'admin'
        password = 'nexenta'

    if (not enc):
        if (user == '' or password == ''):
            print "\nyou must supply either an encoded credential or both user and password values\n"
            usage(1)
        else:
            cred = '%s:%s' % (user, password)
            encoded_cred = cred.encode('base64')[:-1]

    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Basic %s' % encoded_cred
    }

    if (len(args) == 2):
        (path, quota) = args
    elif (len(args) == 1):
        (path) = args[0]
    else:
        print"\nincorrect number of arguments\n"
        usage(1)

    # validate path
    if (not re.match("^[a-zA-Z0-9\._\-/]*$", path)):
        print "\n%s is not a valid path value\n" % path
        sys.exit(1)
    if (re.match("^/", path)):
        print "\npath cannot start with '/'\n"
        sys.exit(1)

    # validate share name
    if (cifs):
        if (not re.match("^[a-zA-Z0-9\._\-]*$", sharename)):
            print "\n%s is not a valid share name\n" % sharename
            sys.exit(1)

    # validate quota value
    if (not re.match("^(none|[0-9]+[kKmMgGtT])$", quota)):
        print "\n%s is not a valid quota value\n" % quota
        sys.exit(1)

    if (not nfs and not cifs):
        print "\nyou must request either NFS or CIFS share\n"
        usage(1)

    url = 'http://%s:%d/rest/nms' % (server, port)

    # first check status -- does it exist? if not, rest call will fail and exit(1)
    #                       is it already shared?  If so just update the quota
    response = nza_rest('folder', 'get_child_props', [path, '^share'])

    if (response['result']['sharenfs'] != 'off' or response['result']['sharesmb'] != 'off'):
        print '%s is already shared, only updating quota to %s' % (path, quota)
        quotaonly = True

    if (not quotaonly):
        if (nfs):
            response = nza_rest('netstorsvc', 'share_folder', [svcname, path,
                                {'anonymous': 'false', 'anonymous_rw': 'false', 'auth_type': 'sys'}])
            response = nza_rest('folder', 'set_child_prop', [path, 'nbmand', 'on'])
        elif (cifs):    # just paranoia, else should be sufficient
            response = nza_rest('netstorsvc', 'share_folder', [svcname, path,
                                {'anonymous_rw': 'false', 'name': sharename}])
            response = nza_rest('folder', 'set_child_prop', [path, 'nbmand', 'on'])

    # update the quota
    response = nza_rest('folder', 'get_child_props', [path, '^quota'])
    if (quota != response['result']['quota']):
        response = nza_rest('folder', 'set_child_prop', [path, 'quota', quota])
    else:
        print "\nquota for %s already set to %s\n" % (path, quota)


if __name__ == "__main__":
    main()

