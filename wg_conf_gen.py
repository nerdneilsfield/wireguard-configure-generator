import argparse
import logging
import os
import subprocess
import sys


def check_wg_exists():
    """check if the wireguard is installed"""
    if (not os.path.exists('/usr/bin/wg')) and (
        not os.path.exists('/usr/local/bin/wg')
    ):
        logging.error(
            'Wireguard not installed, please install wireguard first'
        )
        sys.exit(1)


def gen_key_pair() -> (str, str):
    genkey_output = subprocess.check_output(['wg', 'genkey'])
    key = genkey_output.decode('utf-8').strip()
    genpubkey_output = subprocess.check_output(
        ['wg', 'pubkey'], input=key.encode('utf-8')
    )
    pubkey = genpubkey_output.decode('utf-8').strip()

    return (key, pubkey)

