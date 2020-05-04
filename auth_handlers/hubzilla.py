# Holly Lotor Montalvo 2020
# Cross - a cross-poster between Mastodon and Hubzilla accounts. (yeah, I know, original name)
# The purpose of this file is to accept credentials for Hubzilla accounts, verify their validity, and save
# the credentials to the userdata file.

# *** BEGIN HOLLY RANT TIME ***
# So the Hubzilla documentation for the OAuth workflow is essentially non-existent. The documentation examples
# for its API essentially have you pass the channel name and the password to the endpoint, and provide no detail as to
# how to go through an OAuth workflow, or how they've even implemented it. I spent a good few hours sifting through
# server source code, trying to figure out how OAuth was implemented and how to get it working. But, no matter what I
# do, it... just won't, and I can't tell if it's a failing on my part, or if their OAuth implementation is just hot
# garbage. But, seeing as though I've never actually seen an application like this that works with the Hubzilla API...
# I'm inclined to believe the latter. Needless to say, I'm definitely not going to implement this into a webapp. I'd
# rather be caught dead than having a webapp that stores its passwords in plaintext (not gonna pull a Sony), and
# forcing me to enter my password to this app every time I want to post feels like it defeats the convenience I was
# hoping for it to have.

# Although, what I might consider is doing something like the good password managers of current do, where information is
# encrypted two-way and is done so such a large number of times that attempting to brute force would be computationally
# expensive beyond reason, but only takes, like, 2-3 seconds if you have the correct password. Maybe down the line...

# ***  END HOLLY RANT TIME  ***

import base64
import getpass
import re
import requests
import json
# We need a whole slew of things. There's no API wrapper for Hubzilla, so we kinda have to roll our own.
# requests will be used to actually send web requests to the instance for validation.
# re will be used to perform a tad bit of sanitation on some of the user input.
# getpass will be used to avoid having the password echoed to the screen when typed.
# base64 will be used to encode the userdata sent to the instance.


# Function to check if the instance has a host-meta page in the /.well-known/ directory.
# The base Hubzilla install has this up, and it's kinda necessary for federation to work.
# That being said, this IS a heuristic - there are plugins for Hubzilla that explicitly disable federation.
# Might be worth looking down the line to see if there's a configuration that makes a valid instance fail this check.
def basic_check(instance):
    host_meta_url = "https://" + instance + "/.well-known/host-meta"
    # Sends a web request to the host-meta page on the instance given.
    host_meta = requests.request("GET", host_meta_url)
    # Check to see if the request returned with a 200 OK status code and return T/F based on that.
    if host_meta.status_code == 200:
        return True
    else:
        return False


# Check if the instance has a node_info page. If so, we can 100% confirm or deny it's a Hubzilla instance.
def check_nodeinfo(instance):
    nodeinfo_url = "https://" + instance + "/nodeinfo/2.0"
    nodeinfo_req = requests.request("GET", nodeinfo_url)
    if nodeinfo_req.status_code == 404:
        # The nodeinfo check failed completely, but this is inconclusive.
        # The Diaspora Statistics plugin has to be enabled for this check to work on a Hubzilla instance.
        # So, we're just gonna return True.
        return True
    # Obtain a JSON-formatted version of the returned data.
    nodeinfo = nodeinfo_req.json()
    # Check the key under software.name. /nodeinfo/2.0 on my instances returns hubzilla, and /1.0 returns redmatrix.
    # I'm including them both for sanity's sake.
    if nodeinfo["software"]["name"] in ("hubzilla", "redmatrix"):
        return True
    else:
        # If we get here, this key doesn't exist or includes something other than those two names.
        # We're going to assume this is not a Hubzilla instance.
        return False


# Attempts to authenticate and pull info using the credentials given using the Hubzilla API.
def check_usercred(instance, channel_name, password):
    # Put the username and password into this odd format required for basic web auth.
    usercheck_creds = channel_name + ":" + password
    # This then needs to be base64 encoded. (At least, it appears to, based on the examples I'm referring to...)
    usercheck_cred64 = str(base64.b64encode(usercheck_creds.encode("utf-8")), "utf-8")
    # And then we put this into the authorization header.
    usercheck_header = {'authorization': "Basic " + usercheck_cred64}

    # Any API call that requires authentication should do here. I'm just using the basic channel export API function.
    usercheck_url = "https://" + instance + "/api/z/1.0/channel/export/basic"
    # Specifying the absolute basics, I only care about the status code.
    usercheck_params = {"sections": "channel", "posts": "0"}
    # Actually put forth the request.
    usercheck = requests.request("POST", usercheck_url, data="", headers=usercheck_header, params=usercheck_params)

    # If the request came out OK, return True. If not, return False.
    if usercheck.status_code == 200:
        return True
    else:
        return False



def main():
    # Let's initialize variables for all the information that we need.
    account_name = ""
    account_type = 1  # Mastodon accounts are 0, Hubzilla accounts 1. May add support for more accounts down the line.
    instance = ""
    channel_name = ""
    password = ""

    # Make a pretty intro screen.
    print("Cross - a Mastodon/Hubzilla cross-poster")
    print("       Holly Lotor Montalvo  2020       ")
    print("----------------------------------------", end="\n\n")

    # Ask for the instance name.
    instance = input("Please enter your instance's domain (i.e. example.com): ")
    # Strip information that might exist out of the URL, if it does.
    instance = re.sub("^https?://", "", instance)   # Removes http(s) from the beginning.
    instance = re.sub("/.*$", "", instance)         # This *should* remove everything after the domain name.

    # Apply a few checks to ensure the instance given is (likely) a valid Hubzilla instance.
    # Neither are a perfect science, unfortunately.
    if basic_check(instance) is False:
        # If we get here, the host-meta page failed to return properly, a page that exists by default on Hubzilla.
        # We're going to assume, therefore, that this instance is not working properly, if it's even an instance.
        # Either that, or someone made an error that even regex can't fix.
        print("Instance returned error upon validation. Something's amiss with the instance. Bailing...")
        # I know it might not necessarily be the cleanest thing on Earth to bail in the middle of the code, but
        # it honestly makes sense to me in this situation to bail at this point, and it makes less sense to drag
        # out the execution all the way to the end with a bunch of else blocks.
        exit(1)
    if check_nodeinfo(instance) is False:
        # If we get here, the nodeinfo page returned, but it appears to have software that isn't Hubzilla.
        # We're going to assume that they typed in the URL of an instance running other software - i.e. Mastodon
        print("Nodeinfo claims this isn't a Hubzilla instance. Bailing...")
        exit(1)

    # Now, we can ask for the user information.
    channel_name = input("Please enter your channel name (this is what goes before @" + instance + "): ")
    channel_name = re.sub("^@", "", channel_name)   # Remove leading @, should they add it themselves.
    pword = getpass.getpass(prompt='Enter your password: ')

    # Attempt to use the credentials. Bail if fails.
    if check_usercred(instance, channel_name, pword) is False:
        print("Authorization attempt failed. Bailing...")
        exit(1)
    # Create the account name based on channel name and instance domain.
    account_name = "@" + channel_name + "@" + instance


if __name__ == '__main__':
    main()