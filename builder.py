#! /usr/bin/python

import argparse
import os
from pathlib import Path

def define_command_line_args() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
                    prog='builder',
                    description='organizes Qt and KDE Building process on archlinux',
                    epilog='')

    parser.add_argument('--packages', help="The name of the list you want to build now.")
    parser.add_argument('--list-packages', help="The name of the list you want to build now.", action="store_true")
    parser.add_argument('--pretend', help="Do not run, just output the commands that would run", action="store_true")
    parser.add_argument('--verbose', help="Don't be shy on output", action='store_true')
    parser.add_argument('--testing', help="Build on a testing repository", action="store_true")
    parser.add_argument('--create_package_folder', help="creates the package folders if they don't exist", action="store_true")
    return parser

def get_packages(script_dir: str) -> [str]:
    subfolders = [ f.name for f in os.scandir(f'{script_dir}/package-list') if f.is_dir() ]
    return subfolders

def check_pkgdest() -> bool:
    makepkgs = [
        f'{Path.home()}/.config/pacman/makepkg.conf',
        f'{Path.home()}/.makepkg.conf',
        '/etc/makepkg.conf'
    ]

    for makepkg in makepkgs:
        try:
            with open(makepkg) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('#'):
                        continue

                    if line.startswith('PKGDEST'):
                        return True
        except:
            continue

    return False

def main():
    pass

if __name__ == "__main__":
    parser = define_command_line_args()
    args = parser.parse_args()
    if not check_pkgdest():
        print("Please set pkgdest in your makepkg.conf")
        exit(1)

    script_dir = os.path.dirname(os.path.realpath(__file__))
    packages = get_packages(script_dir)

    if args.list_packages:
        print("Available package list:")
        for package in packages:
            print(f'\t{package}')
    
    main()
