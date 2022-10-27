# wireguard-configure-generator

A very simple wireguard configure generator.

Just one config json file, whole network wireguard configurated.


## Dependencies

No other dependencies except python standard library.

## Usage

```bash
usage: wg_conf_gen.py [-h] [-c CONFIG] [-o OUTPUT] [--gen-example]
                      [--gen-example-path GEN_EXAMPLE_PATH]

generate wireguard config files from json file

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        the path to configuration file
  -o OUTPUT, --output OUTPUT
                        the path to output directory
  --gen-example         flag to enable generate example
  --gen-example-path GEN_EXAMPLE_PATH
                        output a example json configuration file
```

1. make a directory to store the output configuration: `mkdir output`
2. Use `python wg_conf_gen.py --gen-example --gen-example-path output/config.json` to generate a sample `config.json`
3. Put your network topology in configuration file: `vim output/config.json`
4. Genenerate your wireguard configuration files: `python wg_conf_gen.py -c output/config.json -o output`

## Configuration

The configuration json file can be devide into three different types:
1. common configuration
2. server configuration
3. client configuration


**common configuration:**

```json
    "common": {
        "network_ipv4_addr": "10.0.0.0/24",
        "network_name": "my-network"
    },
```

**server configuration:**

```json
    "server": {
        "interface": "en0",
        // real ipv4 addr
        "ipv4_addr": "10.0.0.1",
        "name": "my-server",
        // expose port
        "port": 8080,
        "vlan_ipv4_addr": "114.114.11.11"
    }
```

**client configuration:**

```json
    "clients": [
        {
            "dns1": "1.1.1.1",
            "dns2": "114.114.114.114",
            "gen_global": true,
            "gen_local": true,
            "name": "my-clients",
            "port": 8080,
            "vlan_ipv4_addr": "10.0.0.2"
        }
    ],
```


## BSD-3 License

```
BSD 3-Clause License

Copyright (c) 2022, DengQi
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```
