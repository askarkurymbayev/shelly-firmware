#!/usr/bin/env python3
"""
Shelly firmware binary download tool.
Rewritten to use subprocess instead of the 'sh' library for compatibility
with Python 3.7+ and modern environments.
"""

import io
import os
import re
import sys
import json
import shutil
import tempfile
import hashlib
import zipfile
import argparse
import subprocess
import requests
import logging

VERSION = '0.2'

CLOUD_URL = 'http://api.shelly.cloud/files/firmware'
FLASH_SIZE = 2097152  # 2MB

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Paths to external tools (must be built via build_tools.sh)
TOOL_MKSPIFFS = os.path.join(os.path.dirname(__file__), 'tools', 'mkspiffs8')
TOOL_UNSPIFFS = os.path.join(os.path.dirname(__file__), 'tools', 'unspiffs8')


# ---------------------------------------------------------------------------
# Helper: run external command via subprocess (replaces 'sh' library)
# ---------------------------------------------------------------------------

class CommandResult:
    """Simple container to hold subprocess result, mirrors old sh-style access."""
    def __init__(self, returncode, stdout, stderr):
        self.exit_code = returncode
        self.stdout = stdout if isinstance(stdout, bytes) else stdout.encode()
        self.stderr = stderr if isinstance(stderr, bytes) else stderr.encode()

    def stdout_str(self):
        return self.stdout.decode(sys.stdout.encoding, errors='replace')

    def stderr_str(self):
        return self.stderr.decode(sys.stderr.encoding, errors='replace')


def run_command(tool_path, *args):
    """
    Run an external binary with the given arguments.
    Returns a CommandResult object.
    Raises FileNotFoundError if the tool binary does not exist.
    """
    if not os.path.isfile(tool_path):
        raise FileNotFoundError(
            f"Tool not found: {tool_path}\n"
            "Please run ./build_tools.sh first to compile the required tools."
        )

    cmd = [tool_path] + [str(a) for a in args]
    logger.debug("Running command: {}".format(' '.join(cmd)))

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    return CommandResult(result.returncode, result.stdout, result.stderr)


# ---------------------------------------------------------------------------
# Cloud API helpers
# ---------------------------------------------------------------------------

def list_dev_from_cloud():
    """Fetch the list of available firmware packages from shelly.cloud."""
    try:
        logger.debug("Fetching data from URL: {}".format(CLOUD_URL))
        cloud_resp = requests.get(CLOUD_URL, timeout=15)
        cloud_resp.raise_for_status()
    except requests.RequestException as err:
        logger.error("An error occurred while fetching device list: {}".format(err))
        sys.exit(1)

    logger.debug("Got response {} for URL: {}".format(cloud_resp.status_code, CLOUD_URL))
    cloud_json = cloud_resp.json()

    if 'isok' in cloud_json and cloud_json['isok']:
        logger.debug("Data JSON received and it looks sane. isok = True")
        return cloud_json['data']

    logger.error("Unexpected response from shelly.cloud: {}".format(cloud_json))
    sys.exit(1)


def print_devices(data, beta=False):
    """Print a formatted table of available devices."""
    print('#' * 56)
    print("The following devices were found in Shelly cloud\n")
    print("{0:<16}{1:<40}".format("Model", "Release"))
    print('=' * 56)

    for model, info in data.items():
        try:
            version = info["beta_ver"] if beta else info["version"]
            print("{0:<16}{1:<40}".format(model, version))
        except KeyError:
            logger.debug("No firmware version available for model {}".format(model))

    print('#' * 56)


def get_firmware_url(data, model, beta=False):
    """Return the firmware download URL for the given model."""
    if model not in data:
        logger.error("Model {} not found in Shelly cloud".format(model))
        sys.exit(1)

    dev_info = data[model]
    logger.debug("Model {} found!".format(model))

    if beta and "beta_url" in dev_info:
        return dev_info["beta_url"]
    return dev_info["url"]


# ---------------------------------------------------------------------------
# Firmware helpers
# ---------------------------------------------------------------------------

def fw_get_manifest(fw_zip):
    """Parse and return the manifest JSON from the firmware zip."""
    firmware_files = fw_zip.namelist()
    logger.debug("Files in firmware package:\n\t{}".format('\n\t'.join(firmware_files)))

    try:
        manifest_name = next(f for f in firmware_files if "manifest" in f)
    except StopIteration:
        logger.error("Manifest file was not found in firmware package!")
        sys.exit(1)

    logger.debug("Manifest file: {}".format(manifest_name))
    manifest_raw = fw_zip.read(manifest_name)

    try:
        return json.loads(manifest_raw)
    except json.JSONDecodeError as err:
        logger.error("Cannot decode manifest JSON: {}".format(err))
        sys.exit(1)


def fw_get_part(fw_zip, part):
    """Extract a named part from the firmware zip."""
    firmware_files = fw_zip.namelist()
    logger.debug("Searching for part '{}' in firmware package".format(part))

    try:
        part_name = next(f for f in firmware_files if part in f)
    except StopIteration:
        logger.error("Part '{}' not found in firmware package".format(part))
        sys.exit(1)

    logger.debug("Part '{}' found as file '{}'".format(part, part_name))
    return bytearray(fw_zip.read(part_name))


def fw_verify_part(data, chksum):
    """Verify SHA1 checksum of a firmware part."""
    logger.debug("Verifying part checksum...")
    digest = hashlib.sha1(data).hexdigest()
    logger.debug("Data checksum:     {}".format(digest))
    logger.debug("Manifest checksum: {}".format(chksum))

    if chksum == digest:
        logger.debug("Checksums match. Success!")
        return True

    logger.warning("Checksum mismatch!")
    return False


def create_flash_image(size):
    """Create a blank flash image filled with 0xFF bytes."""
    logger.debug("Generating empty flash image of {} bytes".format(size))
    return bytearray([0xFF] * size)


# ---------------------------------------------------------------------------
# SPIFFS / hwinfo injection
# ---------------------------------------------------------------------------

def mk_hwinfo_for_platform(name):
    """Build the hwinfo_struct.json content for the given platform name."""
    hwinfo = {
        "selftest": True,
        "hwinfo_ver": 1,
        "batch_id": 1,
        "model": name,
        "hw_revision": "prod-unknown",
        "manufacturer": "device_recovery"
    }
    return json.dumps(hwinfo)


def fs_inject_hwinfo(data, name):
    """
    Unpack SPIFFS image, inject hwinfo_struct.json, and repack.
    Uses subprocess-based run_command() instead of the 'sh' library.
    """
    temp_dir = tempfile.mkdtemp()
    fs_dir = os.path.join(temp_dir, 'out')
    fs_old = os.path.join(temp_dir, 'old.bin')
    fs_new = os.path.join(temp_dir, 'new.bin')
    os.mkdir(fs_dir)

    logger.debug("Temp directory for SPIFFS: {}".format(temp_dir))

    # Write current SPIFFS image to disk
    with open(fs_old, 'wb') as f:
        f.write(data)

    # --- Unpack SPIFFS ---
    cmd = run_command(TOOL_UNSPIFFS, '-d', fs_dir, fs_old)

    if cmd.exit_code != 0:
        logger.error(
            "SPIFFS unpacking failed!\n"
            "\tStdout: {}\n"
            "\tStderr: {}".format(cmd.stdout_str(), cmd.stderr_str())
        )
        shutil.rmtree(temp_dir, ignore_errors=True)
        sys.exit(1)

    logger.debug(
        "SPIFFS unpack success!\n"
        "\tStdout: {}\n"
        "\tStderr: {}".format(cmd.stdout_str(), cmd.stderr_str())
    )

    # unspiffs prints FS parameters to stderr
    cmd_info = cmd.stderr_str()

    def extract_param(pattern, text, label):
        match = re.search(pattern, text)
        if not match:
            logger.error("Could not parse '{}' from unspiffs output".format(label))
            sys.exit(1)
        return match.group(1)

    fs_fs = extract_param(r'\(.*?fs\s+(\d+).*?\)', cmd_info, 'fs size')
    fs_bs = extract_param(r'\(.*?bs\s+(\d+).*?\)', cmd_info, 'block size')
    fs_ps = extract_param(r'\(.*?ps\s+(\d+).*?\)', cmd_info, 'page size')
    fs_es = extract_param(r'\(.*?es\s+(\d+).*?\)', cmd_info, 'erase size')

    # Write hwinfo
    hwinfo = mk_hwinfo_for_platform(name)
    logger.debug("Created hwinfo: {}".format(hwinfo))

    hwinfo_path = os.path.join(fs_dir, 'hwinfo_struct.json')
    with open(hwinfo_path, 'w') as f:
        f.write(hwinfo)

    # --- Repack SPIFFS ---
    cmd = run_command(
        TOOL_MKSPIFFS,
        '-s', fs_fs,
        '-b', fs_bs,
        '-p', fs_ps,
        '-e', fs_es,
        '-f', fs_new,
        fs_dir
    )

    if cmd.exit_code != 0:
        logger.error(
            "SPIFFS repacking failed!\n"
            "\tStdout: {}\n"
            "\tStderr: {}".format(cmd.stdout_str(), cmd.stderr_str())
        )
        shutil.rmtree(temp_dir, ignore_errors=True)
        sys.exit(1)

    logger.debug(
        "SPIFFS repack success!\n"
        "\tStdout: {}\n"
        "\tStderr: {}".format(cmd.stdout_str(), cmd.stderr_str())
    )

    with open(fs_new, 'rb') as f:
        new_data = bytearray(f.read())

    shutil.rmtree(temp_dir, ignore_errors=True)
    return new_data


# ---------------------------------------------------------------------------
# Firmware build
# ---------------------------------------------------------------------------

def build_firmware(input_data, output_file):
    """Parse firmware zip, process all parts, and write a single binary image."""
    fw_zip = zipfile.ZipFile(io.BytesIO(input_data))
    manifest = fw_get_manifest(fw_zip)

    try:
        platform_name = manifest['name']
    except KeyError:
        logger.error("Platform name not found in firmware manifest")
        sys.exit(1)

    logger.info("Found platform {} in firmware package".format(platform_name))

    part_list = []
    logger.debug("Iterating over firmware parts...")

    for key, part in manifest['parts'].items():
        start_addr = part["addr"]
        part_size = part["size"]

        has_fill = "fill" in part
        has_src = "src" in part

        if not has_fill and not has_src:
            logger.error("Data missing for part '{}'.".format(key))
            sys.exit(1)

        if has_fill:
            part_data = bytearray([part["fill"]] * part_size)

        if has_src:
            part_data = fw_get_part(fw_zip, part["src"])

        if "cs_sha1" in part:
            if not fw_verify_part(part_data, part["cs_sha1"]):
                logger.error("Verification failed for part '{}'".format(key))
                sys.exit(1)

        logger.debug(
            "Part '{}':\n"
            "\tStart address: {}\n"
            "\tSize: {}\n"
            "\tData (first 32 bytes): {}...".format(
                key,
                hex(int(start_addr)),
                hex(int(part_size)),
                ''.join(format(x, '02x') for x in part_data[:32])
            )
        )

        if 'fs' in key:
            logger.debug("Found SPIFFS partition of size: {}".format(part_size))
            part_data = fs_inject_hwinfo(part_data, platform_name)
            part_size = len(part_data)
            logger.debug("New SPIFFS partition size: {}".format(part_size))

        part_list.append({
            'start': start_addr,
            'size': part_size,
            'data': part_data
        })

    # Assemble final flash image
    empty_image = create_flash_image(FLASH_SIZE)
    flash_image = io.BytesIO(empty_image)

    for part in part_list:
        logger.debug("Writing {} bytes at address {}...".format(
            part['size'], hex(int(part['start']))
        ))
        flash_image.seek(part['start'])
        flash_image.write(part['data'])

    with open(output_file, "wb") as outfile:
        logger.info("Writing output file: {}".format(output_file))
        outfile.write(flash_image.getbuffer())

    logger.info("Done! Firmware image written to: {}".format(output_file))


def download_and_build_firmware(url, output_file):
    """Download firmware zip from URL and build binary image."""
    logger.info("Downloading firmware from: {}".format(url))
    try:
        fw_pkg = requests.get(url, timeout=60)
        fw_pkg.raise_for_status()
    except requests.RequestException as err:
        logger.error("An error occurred while fetching firmware: {}".format(err))
        sys.exit(1)

    build_firmware(fw_pkg.content, output_file)


def build_firmware_from_file(input_file, output_file):
    """Read firmware zip from local file and build binary image."""
    try:
        with open(input_file, "rb") as f:
            file_contents = f.read()
    except OSError as err:
        logger.error("An error occurred while reading input file: {}".format(err))
        sys.exit(1)

    build_firmware(file_contents, output_file)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Shelly firmware binary download and build tool v{}".format(VERSION)
    )
    parser.add_argument(
        "-l", "--list", action="store_true",
        help="List available devices from shelly.cloud"
    )
    parser.add_argument(
        "-b", "--beta", action="store_true",
        help="Use beta firmware versions"
    )
    parser.add_argument(
        "-d", "--download", dest="model",
        help="Download and build firmware binary for the specified device model (e.g. SHSW-1)"
    )
    parser.add_argument(
        "-i", "--input", dest="input_file",
        help="Use a local .zip file as input instead of downloading"
    )
    parser.add_argument(
        "-o", "--output", default="firmware.bin",
        help="Output file name (default: firmware.bin)"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable verbose debug output"
    )

    args = parser.parse_args()

    # Configure logging
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(levelname)s:\t%(message)s'))
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler('shelly_firmware.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter('%(asctime)s\t[%(levelname)s]: %(message)s')
    )
    logger.addHandler(file_handler)

    logger.info("Shelly firmware binary download tool. Version {}".format(VERSION))

    if args.list:
        logger.info("Getting list of available firmware packages from shelly.cloud")
        dev_list = list_dev_from_cloud()
        print_devices(dev_list, args.beta)
        sys.exit(0)

    if args.model:
        logger.info("Downloading firmware binary file for device {}".format(args.model))
        logger.info("Output file is set to: {}".format(args.output))
        dev_list = list_dev_from_cloud()
        firmware_url = get_firmware_url(dev_list, args.model, args.beta)
        download_and_build_firmware(firmware_url, args.output)
        sys.exit(0)

    if args.input_file:
        logger.info("Building firmware from local file: {}".format(args.input_file))
        logger.info("Output file is set to: {}".format(args.output))
        build_firmware_from_file(args.input_file, args.output)
        sys.exit(0)

    parser.print_help()


if __name__ == "__main__":
    main()
