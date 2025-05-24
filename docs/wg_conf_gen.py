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

def gen_example(path):
    with open(path, "w") as f:
        f.write("""
{
    "clients": [
        {
            "dns1": "10.15.44.11",
            "dns2": "114.114.114.114",
            "gen_global": true,
            "gen_local": true,
            "name": "my-clients",
            "port": 8080,
            "vlan_ipv4_addr": "10.0.0.2"
        }
    ],
    "common": {
        "network_ipv4_addr": "10.0.0.0/24",
        "network_name": "my-network"
    },
    "server": {
        "interface": "en0",
        "ipv4_addr": "10.0.0.1",
        "name": "my-server",
        "port": 8080,
        "vlan_ipv4_addr": "114.114.11.11"
    }
}
    """)


# def gen_server_config(configs):
#     pass
#
#
# def gen_client_config(configs):
#     pass



if __name__ == "__main__":

    check_wg_exists()

    logging.basicConfig(format="%(asctime)s:%(levelname)s: %(message)s", level=logging.INFO)

    arg_parser = argparse.ArgumentParser(description="generate wireguard config files from json file")

    arg_parser.add_argument("-c", "--config", type=str, default="config.json", help="the path to configuration file")
    arg_parser.add_argument("-o", "--output", type=str, default=".", help="the path to output directory")
    arg_parser.add_argument("--gen-example", action="store_true", default=False, help="flag to enable generate example")
    arg_parser.add_argument("--gen-example-path", type=str, default="config.example.json", help="output a example json configuration file")

    args = arg_parser.parse_args()

    if args.gen_example:
        gen_example(args.gen_example_path)
        sys.exit(0)

    logging.info(f"loading configuration file {args.config}")
    configs = json.load(open(args.config))
# print(configs)

# keys = {}
    logging.debug("generate keys for server and clients")
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
    logging.info("generate config file for server")
    server_config_name = (
        f"wg-{configs['common']['network_name']}-server-{configs['server']['name']}.conf"
    )
    server_config_path = os.path.join(os.path.abspath(args.output), server_config_name)

    with open(server_config_path, "w") as f:
        server = configs["server"]
        common = configs["common"]
        server_interface = server["interface"]
        network_name = common["network_name"]
        f.write(
        f"""[Interface]
Address = {server["vlan_ipv4_addr"]}/24
ListenPort = {server["port"]}
PrivateKey = {server["prvkey"]}
PostUp = iptables -A FORWARD -i {server_interface} -o {network_name} -j ACCEPT; iptables -A FORWARD -i {network_name} -j ACCEPT; iptables -t nat -A POSTROUTING -o {server_interface} -j MASQUERADE
PostDown = iptables -D FORWARD -i {server_interface} -o {network_name} -j ACCEPT; iptables -D FORWARD -i {network_name} -j ACCEPT; iptables -t nat -D POSTROUTING -o {server_interface} -j MASQUERADE
    """
    )
        for client in configs["clients"]:
            f.write(f"""
### Client {client["name"]}
[Peer]
PublicKey = {client["pubkey"]}
PresharedKey = {client["psk"]}
AllowedIPs = {client["vlan_ipv4_addr"]}/32
""")

# gen client config
    for client in configs["clients"]:
        logging.info(f'generate config fie for client {client["name"]}')
        server = configs["server"]
        common = configs["common"]
        common_header = f"""[Interface]
PrivateKey = {client["prvkey"]}
Address = {client["vlan_ipv4_addr"]}/32
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
            config_global_path = os.path.join(os.path.abspath(args.output), config_global_name)

            global_configs = (
                common_header
                + """AllowedIPs = 0.0.0.0/0
"""
            )

            with open(config_global_path, "w") as f:
                f.write(global_configs)

        if client["gen_local"]:
            config_local_name = (
                f'wg-{common["network_name"]}-client-{client["name"]}-local.conf'
            )
            config_local_path = os.path.join(os.path.abspath(args.output), config_local_name)

            local_configs = (
                common_header
                + f"""AllowedIPs = {common['network_ipv4_addr']}
"""
            )

            with open(config_local_path, "w") as f:
                f.write(local_configs)


    json.dump(configs, open(args.config, "w"))
