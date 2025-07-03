#! /usr/bin/python

import argparse
import os
import subprocess
import textwrap

from pathlib import Path
import argparse

class SmartFormatter(argparse.HelpFormatter):

    def _split_lines(self, text, width):
        if text.startswith('R|'):
            return text[2:].splitlines()  
        return argparse.HelpFormatter._split_lines(self, text, width)

def define_command_line_args():
    parser = argparse.ArgumentParser(
                    prog='builder',
                    description='organizes Qt and KDE Building process on archlinux',
                    epilog='',
                    formatter_class=SmartFormatter)

    parser.add_argument('--package-list',
                            help="The name of the list you want to build now.")
    parser.add_argument('--list-packages',
                            help="List the possible package groups that this script can build.", 
                            action="store_true")
    parser.add_argument('--testing',
                            help="Build on a testing repository",
                            action="store_true")
    parser.add_argument('--repository',
                            help="The target arch-linux target repository",
                            default="extra")
    parser.add_argument('--target-version', 
                            help="The target version of the packages you want to build. Should match tarballs.")
    parser.add_argument('--remote',
                            help="Flag that indicates we are running on build.archlinux.org", 
                            action="store_true")
    parser.add_argument('--buildroot',
                            help="folder where the build will happen",
                            default=f'{Path.home()}/buildroot/')

    parser.add_argument('--packages-to-build', 
                        help="Builds just the list of packages specified in the list",
                        required=False)

    parser.add_argument("--remote-user", help="The folder where to fetch the packages.")

    parser.add_argument('--steps', help='''R|
    1 - clone pkgbuild repositories
    2 - download embargoed  packages
    3 - update pkgbuilds
    4 - connect to ssh and prepare the remote build system
    5 - connect to ssh and prepare the remote build system
    6 - Builds the remote packages
    7 - Release packages
    B - Build packages (remote only)
''', nargs='*')

    args = parser.parse_args()
    return args

def get_packages(script_dir: str) -> [str]:
    subfolders = [ f.name for f in os.scandir(f'{script_dir}/package-list') if f.is_dir() ]
    return subfolders

def get_pkgdest() -> str:
    print("Checking validity of makepkg.conf. Ignore possible errors during check.")
    makepkgs = [
        f'{Path.home()}/.config/pacman/makepkg.conf',
        f'{Path.home()}/.makepkg.conf',
        '/etc/makepkg.conf'
    ]

    for makepkg in makepkgs:
        out = subprocess.check_output(["bash", "-c", f"cat {makepkg} | grep PKGDEST | cut -d'=' -f2 | cut -d'\"' -f2 "])
        value = out.decode()[0]
        if len(value):
            return value

    # the above return always work
    return "" # never runs.

def check_pkgdest() -> bool:
    print("Checking validity of makepkg.conf. Ignore possible errors during check.")
    makepkgs = [
        f'{Path.home()}/.config/pacman/makepkg.conf',
        f'{Path.home()}/.makepkg.conf',
        '/etc/makepkg.conf'
    ]

    for makepkg in makepkgs:
        out = subprocess.check_output(["bash", "-c", f'cat  {makepkg} | grep "PKGDEST\|PACKAGER" | wc -l'])
        value = out.decode()[0]
        if not value in ["0", "1"]:
            print("Check Finished")
            return True

    print("Check Finished")
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
        print("Please set PKGDEST and PACKAGER in your makepkg.conf")
        exit(1)

    if args.target_version is None:
        print("Please specify the version of the packages you want to build.")
        exit(1)

    buildroot = args.buildroot

    repository = args.repository
    if args.testing:
        repository += "-testing"

    # Here we push all variables that the shell scripts will need.
    # Make sure the scripts are using those instead of the hardcoded ones.
    os.environ["__BUILDROOT__"] = buildroot
    os.environ["__PKG_LIST__"] = args.package_list
    os.environ["__SCRIPT_ROOT__"] = script_dir
    os.environ["__PKG_REPO_ROOT_PATH__"] = os.path.realpath(f"{script_dir}/../packages/{args.package_list}")
    os.environ["__REMOTE_BUILD__"] = "true" if args.remote else "false"
    os.environ["__REPO__"] = repository
    os.environ["__PKG_VERSION__"] = args.target_version
    os.environ["__STABILITY__"] = "stable"

    if args.remote:
        print("Hello")
        print(f"Setting the buildroot to {buildroot}")

    if args.steps is None or "1" in args.steps:
        print("Starting Step 1 - ")
        subprocess.run([f"{script_dir}/scripts/checkout-packages", "main"])

    if args.steps is None or "2" in args.steps:
        # is there a way, to, programatically know if a package is embargoed?
        subprocess.run([f"{script_dir}/scripts/download-packages"])
        pass

    if args.steps is None or "3" in args.steps:
        subprocess.run([f"{script_dir}/scripts/update-pkgbuilds"])

    # Prepare the build machine to run
    if args.steps is None or "4" in args.steps:
        base_call = ["ssh", "build.archlinux.org"]

        # Make sure we have the necessary information on the server.
        # TODO: I'm checking just for one possible file, check also for ~/.config/makepkg.conf
        out = subprocess.check_output(["ssh", "build.archlinux.org", 'cat  ~/.config/pacman/makepkg.conf | grep "PKGDEST\|PACKAGER" | wc -l'])
        if out.decode() != "2\n":
            print("Please configure your makepkg.conf on build.archlinux.org. you need at least PKGDEST and PACKAGER configured.")
            exit(1)

        # TODO: This is still using the branches. fix this before moving on.
        # TODO: buildroot is currently hardcoded on the branches. this will
        # NOT work with my current code.
        calls = [
            "git clone https://gitlab.archlinux.org/archlinux/kde-build.git",
            # TODO: Remove this checkout
            f"cd kde-build && git fetch && git checkout master && git reset --hard origin/master",
            f"mkdir -p {buildroot}/{repository}-x86_64",
            f"mkarchroot {buildroot}/{repository}-x86_64/root base-devel",
        ]

        for call in calls:
            new_call = [] + base_call
            new_call.append(call)
            print(f"Running {new_call}")
            subprocess.run(new_call)
            print(f"Finished")
    
    if args.steps is None or "5" in args.steps:
        if args.remote_user is None:
            print("Please specify the remote user.")
            exit(1)
        base_call = ["ssh", "build.archlinux.org"]

        # Brief explanation of the calls here:
        # 1 - Update the buildscripts and reset the build infra.
        # 2 - Syncs the packages folder with the local changes to the remote
        # TODO: Unbreak Build on remote.
        calls = [
            f"cd kde-build && git fetch && git checkout master && git reset --hard origin/master && git clean -fxd",
        ]

        for call in calls:
            new_call = [] + base_call
            new_call.append(call)
            out = subprocess.check_output(new_call)
            print(out.decode())        
            print("-------------------")

        out = subprocess.check_output(["rsync", "-uav", f"{script_dir}/../packages/", f"build.archlinux.org:/home/tcanabrava/packages"])

    if args.steps is None or "6" in args.steps:
        base_call = ["ssh", "build.archlinux.org"]
        cmd: str = f"cd kde-build && ./builder.py --remote --package-list={args.package_list} --steps B --repository={repository} --target-version={args.target_version} --buildroot={args.buildroot}"
        if args.packages_to_build is not None:
            print(type(args.packages_to_build))
            cmd += f" --packages-to-build=\"{args.packages_to_build}\""
        
        # TODO: Unbreak Build on remote.
        calls = [
            cmd
        ]

        for call in calls:
            new_call = [] + base_call
            new_call.append(call)
            out = subprocess.check_output(new_call)
            print(out.decode())
            print("-------------------")

    if args.steps is None or "7" in args.steps:
        if args.remote_user is None:
            print("Please specify the remote user.")
            exit(1)

        subprocess.run(["rsync", "-avm", f"build.archlinux.org:/home/{args.remote_user}/pkgdest/", get_pkgdest()])

    # Validate Packages
    # Re-enable this when it makes more sense.
    # currently it's a validation by eye and this is not really useful.
    # if args.steps is None or "8" in args.steps:
    #    subprocess.run([f"{script_dir}/scripts/run-namcap"])
    #    subprocess.run([f"{script_dir}/scripts/run-checkpkg"])

    # Release Packages
    if args.steps is None or "8" in args.steps:
        if args.testing:
            # Run twice, one with -t, and another with --repo
            # This is a regression from devtools.
            subprocess.run([f"{script_dir}/scripts/release-packages", "-t", "-m", f"Update to {args.target_version}"])
            subprocess.run([f"{script_dir}/scripts/release-packages", "--repo", "extra-testing", "-m", f"Update to {args.target_version}"])
        else:
            # TODO: What to do with packages that are newer and not in the repo yet?
            subprocess.run([f"{script_dir}/scripts/release-packages", "-m", f"Update to {args.target_version}"])

    if args.remote and "B" in args.steps:

        print("###############################################################")
        print(f"Trying to build packages for {repository} (remote machine):")
        if args.packages_to_build is None:
            result = subprocess.run(
                [f"{script_dir}/scripts/build-packages", repository],       
                    stdout = subprocess.PIPE,
                    stderr = subprocess.STDOUT,
                    text = True
            )
        else:
            for package in args.packages_to_build.split(' '):
                result = subprocess.run(
                    [f"{script_dir}/scripts/build-single-package", package],       
                    stdout = subprocess.PIPE,
                    stderr = subprocess.STDOUT,
                    text = True
                )
        print(f"Result: {result.stdout}")
        print("If there was an error on this call, make sure you run this script")
        print("Inside of the ssh host to fetch the packages")
        print("###################### END ####################")
        
