import requests
import argparse
import getpass
import json
import sys
import dateutil.parser
from datetime import datetime, timedelta
from time import sleep

# Purpose and motivation
#
# This is to be used with ciscokinetic.io platform
#
# Cisco Kinetic Cloud API documentation:
#    https://eu.ciscokinetic.io/swagger-ui/index.html?url=/api/v2/apidocs#/
# Although not documented, allow ample time between HTTP requests or you'll be
# kicked out swiftly of your API calls are too fast.

# CAVEATS AND KNOWN ISSUES

# Example:
#
# This program will:


def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")


def main():

    parser = argparse.ArgumentParser(description='Check for old users created\
        in one ciscokinetic.io organization.')

    parser.add_argument('--cluster', required=True, choices=['us', 'eu'],
                        help='which cluster to use: "eu" or "us"')
    parser.add_argument('--username', required=True,
                        help='username for ciscokinetic.io\
                        (ie: user@cisco.com)')
    parser.add_argument('--days', required=False, type=int, default=180,
                        help='Number of days to consider a user expired')
    parser.add_argument('org', metavar='org-id', type=int,
                        help='organisation id to check (number)')
    parser.add_argument('--password', help='password for ciscokinetic.io, \
                        will be prompted inteactively if not specified')
    parser.add_argument('--debug', action='store_true', help='be verbose \
                        about what is happening')
    parser.add_argument('--show-all', action='store_true', help='show all, \
                        including non expired users')
    args = parser.parse_args()

    admin_email = args.username
    admin_password = args.password
    org_id_str = str(args.org)
    cluster = "https://" + args.cluster+".ciscokinetic.io"
    debug = args.debug
    show_all = args.show_all
    membership_expired = 0
    membership_total = 0

    print "Using cluster [" + cluster + "] with user '" + admin_email + "'..."

    if not admin_password:
        admin_password = getpass.getpass('Password:')

    if debug:
        print "Using password '" + admin_password + "'"

    # definition of TOKEN URL
    token_url = cluster + '/api/v2/users/access_token'

    if debug:
        print "Requesting token..."

    try:
        token_req = requests.post(token_url, data={
            'email': admin_email, 'password': admin_password})
        token_req.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print "[ERROR]: ", e
        sys.exit(1)

    if debug:
        print 'Token request status: ', token_req

    token_data = token_req.json()
    token = token_data['access_token']

    # define ORGANIZATION URL
    organization_url = cluster + '/api/v2/organizations/'

    # define HEADER
    headers = {
    'Content-Type': "application/json",
    'Accept': "application/json",
    'Cache-Control': "no-cache",
    'Authorization': 'Token {}'.format(token)
    }

    # Build the primary API call structure to request list of users
    # in the given source organisation
    get_members_url = organization_url + org_id_str + "/memberships"

    # Run that request against ciscokinetic and catch errors
    org_post = ''
    try:
        sleep(2)
        org_post = requests.request("GET", get_members_url, headers=headers)
        org_post.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print "[ERROR]: ", e
        sys.exit(1)

    if debug:
        print json.dumps(org_post.json(), sort_keys=True, indent=4)

    # All the users are under the "membership" JSON node. Note that it can
    # only hande 25 users,
    # and if more than 25 users this request should be made multiple times to
    # pull users 25 at a time.
    # This is a limitation imposed by ciscokinetic API.
    members_dict = org_post.json()['memberships']

    print "Users in the organisation " + org_id_str + ":"
    for key in members_dict:
        user = key['user']
        user_name = user['name']
        user_email = user['email']
        created_at_str = key['created_at']  # When was that membership created?
        created_at_dutil = dateutil.parser.parse(created_at_str, ignoretz=True)
        created_at_delta = datetime.now() - created_at_dutil+timedelta(days=3)
        membership_total += 1
        # Create a new org for this specific user
        if (created_at_delta > timedelta(days=args.days)):
            print "+ User: " + user_name + " <" + user_email + ">"
            print "|--- Membership EXPIRED: created '" + \
                str(created_at_delta.days) + "' days ago ... "
            membership_expired += 1
        else:
            if show_all:
                print "+ User: " + user_name + " <" + user_email + ">"
                print "|--- ok, created " + \
                    str(created_at_delta.days) + "' days ago"
    print "TOTAL : " + str(membership_total) + " user(s), EXPIRED: " \
        + str(membership_expired) + " user(s)."
    sys.stdout.flush()
    sys.exit(0)


if __name__ == "__main__":
    main()
