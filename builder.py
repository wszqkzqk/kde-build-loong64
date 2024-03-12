#! /usr/bin/python

import argparse
import os
from pathlib import Path

def define_command_line_args():
    parser = argparse.ArgumentParser(
                    prog='builder',
                    description='organizes Qt and KDE Building process on archlinux',
                    epilog='')

    parser.add_argument('--package-list', help="The name of the list you want to build now.")
    parser.add_argument('--list-packages', help="The name of the list you want to build now.", action="store_true")
    parser.add_argument('--pretend', help="Do not run, just output the commands that would run", action="store_true")
    parser.add_argument('--verbose', help="Don't be shy on output", action='store_true')
    parser.add_argument('--testing', help="Build on a testing repository", action="store_true")
    parser.add_argument('--create_package_folder', help="creates the package folders if they don't exist", action="store_true")
    parser.add_argument('--buildroot',
                            help="folder where the build will happen",
                            default=f'{Path.home()}/buildroot/<pkg-list>')

    args = parser.parse_args()
    return args

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
    args = define_command_line_args()
    script_dir = os.path.dirname(os.path.realpath(__file__))
    packages = get_packages(script_dir)

    if args.list_packages:
        print("Available package list:")
        for package in packages:
            print(f'\t{package}')
        exit(1)

    if args.package_list is None:
        print("Please define the --package-list you want to build")
        print("in doubt, run with --list-packages")
        exit(1)

    if not check_pkgdest():
        print("Please set pkgdest in your makepkg.conf")
        exit(1)

    buildroot = args.buildroot
    if "<pkg-list>" in buildroot:
        buildroot = buildroot.replace("<pkg-list>", args.package_list)

    # Here we push all variables that the shell scripts will need.
    os.environ["__BUILDROOT__"] = buildroot
    os.environ["__PKG_LIST__"] = args.package_list
    os.environ["__SCRIPT_ROOT__"] = script_dir

    main()
