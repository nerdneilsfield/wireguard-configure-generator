import argparse
import logging
import os
import subprocess
import sys
import json


def check_wg_exists():
    """check if the wireguard is installed"""
    if (not os.path.exists("/usr/bin/wg")) and (
        not os.path.exists("/usr/local/bin/wg")
    ):
        logging.error("Wireguard not installed, please install wireguard first")
        sys.exit(1)


def gen_key_pair() -> (str, str, str):
    genkey_output = subprocess.check_output(["wg", "genkey"])
    key = genkey_output.decode("utf-8").strip()
    genpubkey_output = subprocess.check_output(
        ["wg", "pubkey"], input=key.encode("utf-8")
    )
    pubkey = genpubkey_output.decode("utf-8").strip()
    psk_output = subprocess.check_output(["wg", "genpsk"])
    psk = psk_output.decode("utf-8").strip()
    return (key, pubkey, psk)


def gen_server_config():
    pass


def gen_client_config():
    pass


configs = json.load(open(sys.argv[1]))
# print(configs)

# keys = {}
if "prvkey" not in configs["server"].keys():
    server_key_pair = gen_key_pair()
    configs["server"]["prvkey"] = server_key_pair[0]
    configs["server"]["pubkey"] = server_key_pair[1]
    configs["server"]["psk"] = server_key_pair[2]

for client in configs["clients"]:
    if "prvkey" not in client.keys():
        client_key_pair = gen_key_pair()
        client["prvkey"] = client_key_pair[0]
        client["pubkey"] = client_key_pair[1]
        client["psk"] = client_key_pair[2]

# print(configs)

# gen server config
print("Gen config for server")
server_config_name = (
    f"wg-{configs['common']['network_name']}-server-{configs['server']['name']}.conf"
)
server_config_path = os.path.join(os.path.abspath("."), server_config_name)

with open(server_config_path, "w") as f:
    server = configs["server"]
    common = configs["common"]
    server_interface = server["interface"]
    network_name = common["network_name"]
    f.write(
        f"""[Interface]
Address = {server["ipv4_addr"]}/24
ListenPort = {server["port"]}
PrivateKey = {server["prvkey"]}
PostUp = iptables -A FORWARD -i {server_interface} -o {network_name} -j ACCEPT; iptables -A FORWARD -i {network_name} -j ACCEPT; iptables -t nat -A POSTROUTING -o {server_interface} -j MASQUERADE
PostDown = iptables -D FORWARD -i {server_interface} -o {network_name} -j ACCEPT; iptables -D FORWARD -i {network_name} -j ACCEPT; iptables -t nat -D POSTROUTING -o {server_interface} -j MASQUERADE
    """
    )
    for client in configs["clients"]:
        f.write(
            f"""
### Client {client["name"]}
[Peer]
PublicKey = {client["pubkey"]}
PresharedKey = {client["psk"]}
AllowedIPs = {client["ipv4_addr"]}/32
"""
        )

# gen client config
for client in configs["clients"]:
    print("Gen config for client: ", client["name"])
    server = configs["server"]
    common = configs["common"]
    common_header = f"""[Interface]
PrivateKey = {client["prvkey"]}
Address = {client["ipv4_addr"]}/32
DNS = {client["dns1"]},{client["dns2"]}

# server {server["name"]}
[Peer]
PublicKey = {server["pubkey"]}
PresharedKey = {client["psk"]}
Endpoint = {server["ipv4_addr"]}:{server["port"]}
PersistentKeepalive = 25
"""
    if client["gen_global"]:
        config_global_name = (
            f'wg-{common["network_name"]}-client-{client["name"]}-global.conf'
        )
        config_global_path = os.path.join(os.path.abspath("."), config_global_name)

        global_configs = (
            common_header
            + """AllowedIPs = 0.0.0.0/0
"""
        )

        with open(config_global_path, "w") as f:
            f.write(global_configs)

    if client["gen_global"]:
        config_local_name = (
            f'wg-{common["network_name"]}-client-{client["name"]}-local.conf'
        )
        config_local_path = os.path.join(os.path.abspath("."), config_local_name)

        local_configs = (
            common_header
            + f"""AllowedIPs = {common['network_ipv4_addr']}
"""
        )

        with open(config_local_path, "w") as f:
            f.write(local_configs)


json.dump(configs, open(sys.argv[1], "w"))
