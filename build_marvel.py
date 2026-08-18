import re
import subprocess

from build import Build

BUILD_FILE = "./build.py"


def Git(*args: str) -> str:
    """Run a git command and fail loudly if it does not work.

    These used to go through `os.system`, whose exit status nobody read. A rejected commit, a
    checkout mid-rebase, or no git on PATH all looked identical to success: `build.py` had already
    been rewritten, the script reported nothing wrong, and the next run incremented from the new
    number. One skipped version per failure, silently.
    """
    result = subprocess.run(("git",) + args, capture_output=True, text=True)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no output"
        raise RuntimeError(f"git {' '.join(args)} failed ({result.returncode}): {detail}")
    return result.stdout.strip()


def IncreaseVersion() -> str:
    """Bump BUILD in build.py and commit that one file. Returns the new version."""
    # Ask git a harmless question first. Nothing is written until git is known to work, so a
    # missing git or a directory that is not a repository cannot leave the version bumped with no
    # commit to match it.
    Git("rev-parse", "--is-inside-work-tree")

    with open(BUILD_FILE, "r") as f:
        original = f.read()

    # Take the current number from the file, not from the imported class. Python caches bytecode,
    # and a `.pyc` written in the same second as the rewrite still looks fresh, so a second run can
    # import the old number from `__pycache__` while the file on disk already holds the new one.
    # Observed: build.py reading `BUILD = 202` while `Build.BUILD` imported as 201, which would
    # compute 202 again and commit the same version twice. The file is the source of truth.
    current = re.search(r"BUILD = (\d+)", original)
    assert current, f"no BUILD line in {BUILD_FILE}, nothing to bump"

    version = str(int(current.group(1)) + 1)
    file_text = re.sub(r"BUILD = (\d+)", "BUILD = " + version, original)

    with open(BUILD_FILE, "w") as f:
        f.write(file_text)

    # Keep the loaded class in step with the file it just rewrote. Python caches modules, so anyone
    # who imported `Build` before this ran still reads the old number from memory: packaging right
    # after a bump moved build.py to 202 and then named the archive cards-...201.zip.
    Build.BUILD = int(version)

    message = f"Package version {Build.MAJOR}.{Build.MINOR}.{Build.PATCH}.{version}"
    try:
        # Pathspec form, rather than `git add` followed by a bare `git commit`. A bare commit takes
        # everything already in the index, so running this with unrelated work staged put that work
        # in the version commit. Naming the file commits its working-tree content and nothing else.
        Git("commit", "-m", message, "--", BUILD_FILE)
    except RuntimeError:
        # Put the file back. A bump that did not commit is worse than no bump: the number on disk
        # matches no commit, and the next run would increment from it and skip a version.
        with open(BUILD_FILE, "w") as f:
            f.write(original)
        Build.BUILD = int(current.group(1))
        raise

    return version


if __name__ == "__main__":
    print(IncreaseVersion())
