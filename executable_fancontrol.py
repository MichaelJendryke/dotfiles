#!/usr/bin/env python
# -*- coding: utf8 -*-

import os
import sys
import time
import glob
import stat
import os.path

from io import BytesIO
from subprocess import check_output, Popen, PIPE, STDOUT, CalledProcessError

devices_to_check = ['/dev/sg*','/dev/sd*', '/dev/ses*', '/dev/bsg/*', '/dev/es/ses*']
# devices_to_check = ['/dev/bsg/*']

sg_ses_binary = "sg_ses"

if "sg_ses_path" in os.environ:
    sg_ses_binary = os.getenv("sg_ses_path")


def usage():
    print('python fancontrol.py 1-7')
    sys.exit(-1)


def get_requested_fan_speed():
    if len(sys.argv) < 2:
        return usage()
    try:
        speed = int(sys.argv[1])
    except ValueError:
        return usage()
    if not 1 <= speed <= 7:
        return usage()
    return speed


def print_speeds(device):
    for i in range(0, 6):
        print('Fan {} speed: {}'.format(i, check_output(
            [sg_ses_binary, '--index=coo,{}'.format(i), '--get=1:2:11', device])
                                        .decode('utf-8').split('\n')[0]))


def find_sa120_devices():
    devices = []
    seen_devices = set()
    for device_glob in devices_to_check:
        for device in glob.glob(device_glob):
            try:
                stats = os.stat(device)
            except OSError:
                continue
            if not stat.S_ISCHR(stats.st_mode):
                print('Enclosure not found on ' + device)
                continue
            device_id = format_device_id(stats)
            if device_id in seen_devices:
                print('Enclosure already seen on ' + device)
                continue
            seen_devices.add(device_id)
            try:
                output = check_output([sg_ses_binary, device], stderr=STDOUT)
                if b'ThinkServerSA120' in output:
                    print('Enclosure found on ' + device)
                    devices.append(device)
                else:
                    print('Enclosure not found on ' + device)
            except CalledProcessError:
                print('Enclosure not found on ' + device)
    return devices


def format_device_id(stats):
    return '{},{}'.format(os.major(stats.st_rdev), os.minor(stats.st_rdev))


def set_fan_speeds(device, speed):
    print_speeds(device)
    print('Reading current configuration...')
    out = check_output(['sg_ses', '-p', '0x2', device, '--raw'])

    s = out.split()

    for i in range(0, 6):
        print('Setting fan {} to {}'.format(i, speed))
        idx = 88 + 4 * i
        s[idx + 0] = b'80'
        s[idx + 1] = b'00'
        s[idx + 2] = b'00'
        s[idx + 3] = u'{:x}'.format(1 << 5 | speed & 7).encode('utf-8')

    output = BytesIO()
    off = 0
    count = 0

    while True:
        output.write(s[off])
        off = off + 1
        count = count + 1
        if count == 8:
            output.write(b'  ')
        elif count == 16:
            output.write(b'\n')
            count = 0
        else:
            output.write(b' ')
        if off >= len(s):
            break

    output.write(b'\n')
    p = Popen(['sg_ses', '-p', '0x2', device, '--control', '--data', '-'],
              stdout=PIPE, stdin=PIPE, stderr=PIPE)
    print(p.communicate(input=output.getvalue())[0].decode('utf-8'))
    print('Set fan speeds... Waiting to get fan speeds (ctrl+c to skip)')
    try:
        time.sleep(10)
        print_speeds(device)
    except KeyboardInterrupt:
        pass


def main():
    speed = get_requested_fan_speed()
    devices = find_sa120_devices()
    if not devices:
        print('Could not find enclosure')
        sys.exit(1)
    for device in devices:
        set_fan_speeds(device, speed)
    print('\nDone')


if __name__ == '__main__':
    main()
