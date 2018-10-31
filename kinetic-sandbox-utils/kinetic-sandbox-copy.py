import requests
import argparse
import getpass
import json
import sys
from time import sleep
from numpy import genfromtxt

# Purpose and motivation
# 
# This is to be used with ciscokinetic.io platform when doing demos for larger crowds
# Attendees will start a Kinetic GMM sandbox will effectively will add them to a kinetic Org
# ... but with very little privillege in order not to mess up the shared sandbox. 
# To experience the full scale of the training they will
# need to be admins. This program copies users with "Support" status to their own private
# org with Admin privillege.

# Cisco Kinetic Cloud API documentation: 
#    https://eu.ciscokinetic.io/swagger-ui/index.html?url=/api/v2/apidocs#/
# Although not documented, allow ample time between HTTP requests or you'll be
# kicked out swiftly of your API calls are too fast.

# CAVEATS AND KNOWN ISSUES
# Will only handle the first 25 users in the source organisation

# Example:
#
# Users have been added by Cisco DevNet Sandbox to org 2826
# The user that executes the scipt has prepared an orgination 3161 to copy users
# Execute this command:
# user$ ./create-org_list.py --cluster us --username *username* --password *password*  2826 3161 
#
# This program will:
#  * read the users list in organisation 2826 (source) 
#  * prompt for each user if it should be added
#  * if yes, a new sub-org will be created under 3161 with the user's name
#  * the user will be added as an Admin to that organisation



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

	parser = argparse.ArgumentParser(description='Copy users from one ciscokinetic.io organization to another.')

	parser.add_argument('--cluster', required=True, choices=['us', 'eu'], help='which cluster to use: "eu" or "us"')
	parser.add_argument('--username', required=True, help='username for ciscokinetic.io (ie: user@cisco.com)')

	parser.add_argument('srcorg', metavar='src-org-id', type=int, help='organisation id where users are copied from (number)')
	parser.add_argument('dstorg', metavar='dst-org-id', type=int, help='organisation id where users are copied to (number)')

	parser.add_argument('--password', help='password for ciscokinetic.io, will be prompted inteactively if not specified')
	parser.add_argument('--all', action='store_true', help='copy all users without asking')
	parser.add_argument('--debug', action='store_true', help='be verbose about what is happening');
	args = parser.parse_args()

	print args.cluster

	print 'This program reads a CSC file with list of name, email. file.csv'
	print 'The program will prompt for the Kinetic admin email, password, org-id.'
	print 'The program will add the users in the cs file to the org-id.'

	admin_email=args.username
	admin_password=args.password
	src_org_id_str=str(args.srcorg)
	src_org_id_num=args.srcorg
	dst_org_id_str=str(args.dstorg)
	dst_org_id_num=args.dstorg
	cluster="https://" + args.cluster+".ciscokinetic.io"
	debug=args.debug
	user_account = "false"
	user_role = 'Admin'

	print "Using cluster [" + cluster + "] with user '" + admin_email + "'..."


	if not admin_password: 
		admin_password = getpass.getpass('Password:')

	if debug:
		print "Using password '" + admin_password + "'"


	# define TOKEN URL
	token_url = cluster +'/api/v2/users/access_token'

	if debug:
		print "Requesting token..."

	try:
		token_req = requests.post(token_url , data = {'email' : admin_email, 'password' : admin_password})
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


	# Build the primary API call structure to request list of users in the given source organisation
	get_members_url = organization_url + src_org_id_str + "/memberships"

	# Run that request against ciscokinetic and catch errors
	try:
		sleep(2)
		org_post = requests.request("GET", get_members_url, headers=headers)
		org_post.raise_for_status()
	except requests.exceptions.HTTPError as e:
		print "[ERROR]: ", e
		sys.exit(1)

	if debug:
		print json.dumps(org_post.json(), sort_keys=True, indent=4)

	# All the users are under the "membership" JSON node. Note that it can only hande 25 users,
	# and if more than 25 users this request should be made multiple times to pull users 25 at a time.
	# This is a limitation imposed by ciscokinetic API.
	members_dict = org_post.json()['memberships']

	print "Users in the source organisation:"
	for key in members_dict:
		user=key['user'] 
		user_name=user['name']
		user_email=user['email']
		role=key['role']
		# Ditch away admins -- they don't need to be copied over
		if role == 'Admin':
			if debug:
				print 'ignoring ' + user_name + ' <' + user_email + '>'
			continue

		# Create Org name as user name + hash of email adressed reduced to 5 characters
		org_name=user_name + " [" + hex(hash(user_email))[-5:].upper() + "]"
		if not args.all:
			if not query_yes_no("Found user " + user_name + " <" + user_email + ">"):
				continue

		# Create a new org for this specific user
		print "+ User: " + user_name + " <" + user_email + ">"
		print "|--- Creating organisation '" + org_name + "' ... ",
		sys.stdout.flush()

		org_payload = {"organization": {"name" : org_name, "parent_id" : dst_org_id_num, "user_account": user_account}}
		if debug:
			print "POSTing: ", org_payload
		sleep(2)
		try:
			org_post = requests.request("POST", organization_url, json=org_payload, headers=headers)
			org_post.raise_for_status()
		except requests.exceptions.HTTPError as e:
			# This means we can't create the org, most likely the org has been created by a subsequent
			# execution of this script. We take a bet by skipping and not checking here.
			if debug:
				print "[ERROR]: ", e, org_post.json()
			else:
				print "error."
			continue 

		if not debug:
			print "done."

		org_post_data=org_post.json()
		org_id = org_post_data['id']
		org_id_str = str(org_id)

		# We created a new org for the new user, time to add that user
		if debug:
			print 'Organisation ' + org_id_str + ' created with name ' + org_name
		# get org id for use to add user

		#		 add user to org
		membership_url = organization_url + org_id_str + '/memberships'
		mem_payload = {"membership": {"email" : user_email, "name" : user_name, "role": user_role}}

		print "|--- Adding user to organisation as admin ... ",
		sys.stdout.flush()

		sleep(2)
		try:
			membership_post = requests.request("POST", membership_url, json=mem_payload, headers=headers)
			membership_post.raise_for_status()
		except requests.exceptions.HTTPError as e:
			if debug:
				print '[ERROR]: cannot add user ' + user_name + ' <' + user_email + '> to organisation ' +  org_id_str
				print "[ERROR]: ", e, org_post.json()
			else:
				print "error."
			continue

		if debug:
			print 'User ' + user_name + ' <' + user_email + '> added to organisation ' +  org_id_str
		else:
			print "done."

	print 'Goodbye...'
	sys.exit(0)

if __name__== "__main__":
	main()
