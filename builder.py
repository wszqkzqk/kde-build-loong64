#! /usr/bin/python

import argparse
import os
import subprocess
import textwrap

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
    parser.add_argument('--repository', help="The target arch-linux target repository", default="extra")
    parser.add_argument('--target-version', help="The target version of the packages you want to build. Should match tarballs.")
    parser.add_argument('--create_package_folder', help="creates the package folders if they don't exist", action="store_true")
    parser.add_argument('--buildroot',
                            help="folder where the build will happen",
                            default=f'{Path.home()}/buildroot/<pkg-list>')

    parser.add_argument('--steps', help='''
    1 - clone pkgbuild repositories
    2 - download embargoed  packages
    3 - update pkgbuilds
    4 - commit changes to packages
    5 - connect to ssh and prepare the build system
    6 - build the software on the ssh machine
    7 - fetch data from the remote machine to local
    8 - Validate packages
    9 - Release packages
''', nargs='*')

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

    if args.target_version is None:
        print("Please specify the version of the packages you want to build.")
        exit(1)

    buildroot = args.buildroot
    if "<pkg-list>" in buildroot:
        buildroot = buildroot.replace("<pkg-list>", args.package_list)

    # Here we push all variables that the shell scripts will need.
    # Make sure the scripts are using those instead of the hardcoded ones.
    os.environ["__BUILDROOT__"] = buildroot
    os.environ["__PKG_LIST__"] = args.package_list
    os.environ["__SCRIPT_ROOT__"] = script_dir
    os.environ["__PKG_REPO_ROOT_PATH__"] = os.path.realpath(f"{script_dir}/../packages/{args.package_list}")

    if args.steps is None or "1" in args.steps:
        print("Starting Step 1 - ")
        # Here we start the build
        subprocess.run([f"{script_dir}/scripts/checkout-packages", "main"])

    if args.steps is None or "2" in args.steps:
        # is there a way, to, programatically know if a package is embargoed?
        # subprocess.run([f"{script_dir}/scripts/download-packages", "stable", args.target_version])
        pass

    if args.steps is None or "3" in args.steps:
        subprocess.run([f"{script_dir}/scripts/update-pkgbuilds", "stable", args.target_version])

    if args.steps is None or "4" in args.steps:
        subprocess.run([f"{script_dir}/scripts/commit-packages", "main", f"Update to {args.target_version}"])

    # Prepare the build machine to run
    if args.steps is None or "5" in args.steps:
        base_call = ["ssh", "build.archlinux.org"]
        repository = args.repository
        if args.testing:
            repository += "-testing"

        # Make sure we have the necessary information on the server.
        # TODO: I'm checking just for one possible file, check also for ~/.config/makepkg.conf
        out = subprocess.check_output(["ssh", "build.archlinux.org", 'cat  ~/.makepkg.conf | grep "PKGDEST\|PACKAGER" | wc -l'])
        if out.decode() != "2\n":
            print("Please configure your makepkg.conf on build.archlinux.org. you need at least PKGDEST and PACKAGER configured.")
            exit(1)

        # TODO: This is still using the branches. fix this before moving on.
        # TODO: buildroot is currently hardcoded on the branches. this will
        # NOT work with my current code.
        calls = [
            "git clone git@gitlab.archlinux.org:archlinux/kde-build.git"
            f"cd kde-build && git checkout work/branchless", # TODO: Remove this checkout
            f"mkdir -p ~/kde-build-root/{repository}-x86_64",
            f"mkarchroot ~/kde-build-root/{repository}-x86_64/root base-devel",
            "cd kde-build && ./checkout-packages main",
            "cd kde-build && gpg --import build/kwin/keys/pgp/*"
        ]

        for call in calls:
            new_call = [] + base_call
            new_call.append(call)
            subprocess.run(new_call)
    
    if args.steps is None or "6" in args.steps:
        base_call = ["ssh", "build.archlinux.org"]

        calls = [
            "cde kde-build && git pull origin work/branchless" # TODO move this to origin main
            "cd kde-build && ./build-packages extra"
        ]

        for call in calls:
            new_call = [] + base_call
            new_call.append(call)
            subprocess.run(new_call)
    
    # Validate Packages
    if args.steps is None or "8" in args.steps:
        subprocess.run([f"{script_dir}/scripts/run-namcap"])
        subprocess.run([f"{script_dir}/scripts/run-checkpkg"])

    # Release Packages
    if args.steps is None or "9" in args.steps:
        if args.testing:
            # Run twice, one with -t, and another with --repo
            # This is a regression from devtools.
            subprocess.run([f"{script_dir}/scripts/release-packages", "-t", "-m", f"Update to {args.target_version}"])
            subprocess.run([f"{script_dir}/scripts/release-packages", "--repo", "extra-testing", "-m", f"Update to {args.target_version}"])
        else:
            # TODO: What to do with packages that are newer and not in the repo yet?
            subprocess.run([f"{script_dir}/scripts/release-packages", "-m", f"Update to {args.target_version}"])
