#!/usr/bin/python3

import requests
import argparse
import sys
from time import sleep


def main():

    # Command line parsing
    parser = argparse.ArgumentParser(description='test')
    parser.add_argument('--cluster', required=True, choices=['us', 'eu'],
                        help='which cluster to use: "eu" or "us"')
    parser.add_argument('--token', required=True,
                        help='API token for ciscokinetic.io')
    parser.add_argument('--org', metavar='org', type=int,
                        help='organisation id (number)')
    parser.add_argument('--ssidname', required=True,
                        help='gateway WiFi SSID')
    parser.add_argument('--ssidpass', required=True,
                        help='WiFi password')
    parser.add_argument('--gateway', required=True, type=int,
                        help='gateway id to change (number)')

    args = parser.parse_args()
    gateway_id = str(args.gateway)
    wifi_ssid = args.ssidname
    wifi_pre_shared_key = args.ssidpass
    broadcast_ssid_enable = "true"

    cluster = "https://" + args.cluster+".ciscokinetic.io"
    token = args.token
    org = str(args.org)

    print("Using cluster [" + cluster + "].")

    # define ORGANIZATION URL
    org_url = cluster + '/api/v2/organizations/'

    # define HEADER
    headers = {
        'Content-Type': "application/json",
        'Accept': "application/json",
        'Cache-Control': "no-cache",
        'Authorization': 'Token {}'.format(token)
        }

    get_members_url = org_url + org + '/gate_ways'

# Run that request against ciscokinetic and catch errors
    try:
        sleep(2)
        org_post = requests.request("GET", get_members_url, headers=headers)
        org_post.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print("[ERROR]: " + str(e))
        sys.exit(1)

    # print(json.dumps(org_post.json(), sort_keys=True, indent=4))

    # configure wifi
    wifi_payload = {"gate_way_ids": [gateway_id], "wifi_ssid": wifi_ssid,
                    "wifi_pre_shared_key": wifi_pre_shared_key,
                    "broadcast_ssid_enable": broadcast_ssid_enable}
    print(wifi_payload)

    try:
        sleep(1)
        wifi_config_post = requests.request("PUT", get_members_url+'/wifi',
                                            json=wifi_payload, headers=headers)
        wifi_config_post.raise_for_status()
        print ('WiFi Condfig SUCCESS: ' + gateway_id)
    except requests.exceptions.HTTPError as e:
        print("[ERROR]: WiFi Condfig FAILED: " + str(e))
        sys.exit(1)

    print('Goodbye...')
    sys.exit(0)


if __name__ == "__main__":
    main()
