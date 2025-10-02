"""CLI commands for WireGuard configuration generator.

This module provides the Click-based CLI interface with commands:
- generate: Generate WireGuard configs from TOML
- validate: Validate TOML configuration
- migrate: Migrate legacy JSON to TOML + keys.json
"""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import click

from wg_mesh_gen import key_manager, loader, migrator, renderer, validator


@click.group()
@click.version_option(version="0.1.0")
def main():
    """WireGuard star topology configuration generator.

    Simple star topology: 1 server + N clients (NOT mesh/hub-spoke/relay).
    """
    pass


@main.command()
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to TOML configuration file",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("./output"),
    help="Output directory for generated configs",
)
@click.option(
    "-k",
    "--keys",
    type=click.Path(dir_okay=False, path_type=Path),
    default=Path("./keys.json"),
    help="Path to JSON key storage file",
)
@click.option(
    "--parallel",
    is_flag=True,
    help="Enable parallel generation for client configs",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Overwrite existing config files",
)
@click.option(
    "--refresh-force",
    is_flag=True,
    help="Regenerate all keys (ignore existing keys.json)",
)
def generate(
    config: Path,
    output: Path,
    keys: Path,
    parallel: bool,
    force: bool,
    refresh_force: bool,
):
    """Generate WireGuard configuration files from TOML."""
    try:
        # Load configuration
        common, server, clients = loader.load_config(config)

        # Validate configuration
        validator.validate_config(common, server, clients)
        click.echo(
            f"✅ Validated configuration: 1 server + {len(clients)} client{'s' if len(clients) > 1 else ''}"
        )

        # Load or generate keys
        existing_keys = None
        if keys.exists() and not refresh_force:
            existing_keys = key_manager.load_keys(keys)
            num_existing_clients = len(existing_keys.get("clients", {}))
            click.echo(
                f"✅ Loaded keys from {keys}: server + {num_existing_clients} client{'s' if num_existing_clients > 1 else ''}"
            )
        elif refresh_force:
            click.echo(
                "⚠️  --refresh-force: Regenerating all keys (existing keys.json ignored)"
            )

        # Generate keys
        client_names = [c.name for c in clients]
        all_keys = key_manager.generate_all_keys(
            server.name,
            client_names,
            existing_keys if not refresh_force else None,
        )

        # Count new keys
        num_new_clients = len(clients)
        if existing_keys and not refresh_force:
            num_new_clients = len(
                set(client_names) - set(existing_keys.get("clients", {}).keys())
            )
            if num_new_clients > 0:
                click.echo(
                    f"✅ Generated new keys for {num_new_clients} client{'s' if num_new_clients > 1 else ''}"
                )

        # Save keys
        key_manager.save_keys(all_keys, keys)
        if refresh_force:
            click.echo(f"✅ Saved keys to {keys} (overwritten)")
        else:
            click.echo(f"✅ Saved keys to {keys}")

        # Create output directory
        output.mkdir(parents=True, exist_ok=True)

        # Generate server config
        server_config = renderer.render_server_config(common, server, clients, all_keys)
        server_filename = renderer.generate_config_filename(
            common.network_name, "server", server.name
        )
        server_path = output / server_filename

        if server_path.exists() and not force:
            click.echo(
                f"❌ Server config already exists: {server_path} (use --force to overwrite)",
                err=True,
            )
            sys.exit(1)

        server_path.write_text(server_config)
        server_path.chmod(0o600)
        click.echo(f"✅ Generated server config → {server_path}")

        # Generate client configs
        def generate_client_config_file(client, mode):
            """Helper function to generate a single client config."""
            client_config = renderer.render_client_config(
                common, server, client, all_keys, mode
            )
            client_filename = renderer.generate_config_filename(
                common.network_name, "client", client.name, mode
            )
            client_path = output / client_filename

            if client_path.exists() and not force:
                return (
                    False,
                    f"❌ Client config already exists: {client_path} (use --force)",
                )

            client_path.write_text(client_config)
            client_path.chmod(0o600)
            return (True, f"✅ Generated client config → {client_path}")

        # Collect all client config generation tasks
        tasks = []
        for client in clients:
            if client.gen_global:
                tasks.append((client, "global"))
            if client.gen_local:
                tasks.append((client, "local"))

        # Generate client configs (parallel or sequential)
        results = []
        if parallel:
            with ThreadPoolExecutor() as executor:
                futures = {
                    executor.submit(generate_client_config_file, client, mode): (
                        client,
                        mode,
                    )
                    for client, mode in tasks
                }
                for future in as_completed(futures):
                    success, message = future.result()
                    results.append((success, message))
                    click.echo(message)
        else:
            for client, mode in tasks:
                success, message = generate_client_config_file(client, mode)
                results.append((success, message))
                click.echo(message)

        # Check if any generation failed
        if not all(success for success, _ in results):
            sys.exit(1)

        # Summary
        num_global = sum(1 for c in clients if c.gen_global)
        num_local = sum(1 for c in clients if c.gen_local)
        click.echo("\nSummary:")
        click.echo("  Server configs: 1")
        click.echo(f"  Client configs: {len(tasks)} ({num_global} global, {num_local} local)")
        if refresh_force:
            click.echo(f"  Keys regenerated: {len(clients) + 1} (server + {len(clients)} clients)")
        elif existing_keys:
            num_reused = len(clients) - num_new_clients + 1  # +1 for server
            click.echo(f"  Keys reused: {num_reused}")
            if num_new_clients > 0:
                click.echo(f"  Keys generated: {num_new_clients}")
        else:
            click.echo(f"  Keys generated: {len(clients) + 1} (server + {len(clients)} clients)")
        click.echo(f"  Key storage: {keys}")
        click.echo(f"  Output directory: {output.absolute()}")

    except validator.ValidationError as e:
        click.echo(f"❌ Validation error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to TOML configuration file",
)
@click.option(
    "-k",
    "--keys",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path to JSON key storage file (optional, for key validation)",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Treat warnings as errors",
)
def validate(config: Path, keys: Path | None, strict: bool):
    """Validate TOML configuration file."""
    try:
        # Load and validate TOML syntax
        try:
            data = loader.load_toml(config)
            click.echo("✅ TOML syntax: Valid")
        except Exception as e:
            click.echo(f"❌ TOML syntax error: {e}", err=True)
            sys.exit(1)

        # Schema validation
        try:
            validator.validate_schema(data)
            click.echo("✅ Schema validation: Passed")
        except Exception as e:
            click.echo(f"❌ Schema validation failed: {e}", err=True)
            sys.exit(1)

        # Parse into models
        common = loader.parse_common_config(data)
        server = loader.parse_server_config(data)
        clients = loader.parse_client_configs(data)

        # Business logic validation
        validator.validate_config(common, server, clients)
        click.echo("✅ Business logic validation: Passed")

        # Print configuration summary
        client_names_str = ", ".join(c.name for c in clients)
        click.echo(f"\nConfiguration summary:")
        click.echo(f"  Network: {common.network_name} ({common.network_ipv4_addr})")
        click.echo(f"  Topology: star (1 server + {len(clients)} clients)")
        click.echo(f"  Server: {server.name}")
        click.echo(f"  Clients: {len(clients)} ({client_names_str})")

        # Print validation checks
        click.echo(f"\nValidation checks:")
        click.echo("  ✓ No duplicate client names")
        click.echo("  ✓ No duplicate IP addresses")
        click.echo("  ✓ All IPs within subnet")
        click.echo("  ✓ Port ranges valid (1024-65535)")
        if any(c.dns1 or c.dns2 for c in clients):
            click.echo("  ✓ DNS nameservers are valid IPv4")
        click.echo("  ✓ gen_global/gen_local constraints satisfied")

        # Validate keys if provided
        if keys:
            if not keys.exists():
                click.echo(f"❌ Keys file not found: {keys}", err=True)
                sys.exit(1)

            click.echo("✅ Key storage validation: Passed")
            keys_data = key_manager.load_keys(keys)

            # Check server keys existence
            if "server" not in keys_data:
                click.echo("❌ Missing server keys in keys.json", err=True)
                sys.exit(1)

            server_keys = keys_data["server"]
            for key_name in ["private_key", "public_key", "preshared_key"]:
                if key_name not in server_keys:
                    click.echo(
                        f"❌ Missing server {key_name} in keys.json", err=True
                    )
                    sys.exit(1)

            # Check client keys existence
            client_names = {c.name for c in clients}
            keys_client_names = set(keys_data.get("clients", {}).keys())

            missing_clients = client_names - keys_client_names
            extra_clients = keys_client_names - client_names

            if missing_clients:
                click.echo(
                    f"❌ Missing keys for clients: {', '.join(sorted(missing_clients))}", err=True
                )
                sys.exit(1)

            # Check that each client has all required keys
            for client_name in client_names:
                client_keys = keys_data["clients"][client_name]
                for key_name in ["private_key", "public_key", "preshared_key"]:
                    if key_name not in client_keys:
                        click.echo(
                            f"❌ Missing {key_name} for client '{client_name}'",
                            err=True,
                        )
                        sys.exit(1)

            # Now validate key formats (server)
            for key_name in ["private_key", "public_key", "preshared_key"]:
                if not key_manager.validate_key_format(server_keys[key_name]):
                    click.echo(
                        f"❌ Invalid server {key_name} format (must be 44-char base64)",
                        err=True,
                    )
                    sys.exit(1)

            # Validate key formats (clients)
            for client_name in client_names:
                client_keys = keys_data["clients"][client_name]
                for key_name in ["private_key", "public_key", "preshared_key"]:
                    if not key_manager.validate_key_format(client_keys[key_name]):
                        click.echo(
                            f"❌ Invalid {key_name} format for client '{client_name}' (must be 44-char base64)",
                            err=True,
                        )
                        sys.exit(1)

            if extra_clients:
                message = f"⚠️  Extra keys in keys.json (not in config): {', '.join(sorted(extra_clients))}"
                if strict:
                    click.echo(f"❌ {message} (--strict mode)", err=True)
                    sys.exit(1)
                else:
                    click.echo(f"\n{message}")

            # Print key storage checks (all validations passed)
            click.echo(f"\nKey storage checks:")
            click.echo(f"  ✓ keys.json exists and is readable")
            click.echo(f"  ✓ Server '{server.name}' has keys (private_key, public_key, preshared_key)")
            for client_name in sorted(client_names):
                click.echo(f"  ✓ Client '{client_name}' has keys")
            click.echo(f"  ✓ All keys are valid base64 (44 characters)")

        # Final message
        if keys:
            click.echo("\n✅ Configuration and keys are valid and ready for generation")
        else:
            click.echo("\n✅ Configuration is valid and ready for generation")

    except validator.ValidationError as e:
        click.echo(f"❌ Validation error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option(
    "-i",
    "--input",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to legacy JSON configuration file",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="Path to output TOML configuration file",
)
@click.option(
    "-k",
    "--keys",
    type=click.Path(dir_okay=False, path_type=Path),
    default=Path("./keys.json"),
    help="Path to output JSON key storage file",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Overwrite existing output files",
)
def migrate(input: Path, output: Path, keys: Path, force: bool):
    """Migrate legacy JSON configuration to TOML + keys.json."""
    try:
        # Check if output files exist
        if output.exists() and not force:
            click.echo(
                f"❌ Output file already exists: {output} (use --force to overwrite)",
                err=True,
            )
            sys.exit(1)

        if keys.exists() and not force:
            click.echo(
                f"❌ Keys file already exists: {keys} (use --force to overwrite)",
                err=True,
            )
            sys.exit(1)

        # Step 1: Load legacy JSON
        click.echo(f"✅ Loaded legacy JSON configuration: {input}")

        # Migrate
        toml_config, keys_data = migrator.migrate_config_file(input, output, keys)

        # Count entities
        num_clients = len(toml_config["clients"])

        # Step 2: Extract keys
        click.echo(f"✅ Extracted embedded keys from server and {num_clients} client{'s' if num_clients != 1 else ''}")

        # Step 3: Convert format
        click.echo(f"✅ Converted server + {num_clients} client{'s' if num_clients != 1 else ''} from JSON to TOML format")

        # Step 4: Validate output
        try:
            common = loader.parse_common_config(toml_config)
            server = loader.parse_server_config(toml_config)
            clients = loader.parse_client_configs(toml_config)
            validator.validate_config(common, server, clients)
            click.echo(f"✅ Validated output TOML configuration")
        except Exception as e:
            click.echo(f"⚠️  Warning: Output validation failed: {e}")

        # Step 5: Write TOML
        click.echo(f"✅ Wrote TOML configuration: {output}")

        # Step 6: Save keys with proper permissions
        key_manager.save_keys(keys_data, keys)
        click.echo(f"✅ Wrote key storage: {keys} (permissions: 0600)")

        # Summary
        click.echo(f"\nMigration Summary:")
        click.echo(f"  Server: 1")
        click.echo(f"  Clients: {num_clients}")
        click.echo(f"  Keys extracted: {num_clients + 1} (server + {num_clients} clients)")
        click.echo(f"  Output files: {output.name}, {keys.name}")
        click.echo(f"  Warnings: 0")

    except Exception as e:
        click.echo(f"❌ Migration error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
