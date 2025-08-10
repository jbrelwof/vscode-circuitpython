#!/usr/bin/env python3
"""
Script to generate and manage CircuitPython stubs.
Handles repository cloning, stub generation, and virtual environment management.
"""
import argparse
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, TypeVar, Callable, Any,ClassVar, TypedDict

# Configuration
#CIRCUITPYTHON_VERSION = "9.2.8"
CIRCUITPYTHON_VERSION = "10.0.0-beta.2"
DEBUG = True or os.getenv("DEBUG", "false").lower() == "true"

# Setup logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def safe_rmtree(path: Path) -> None:
    """
    Safely remove a directory tree.
    
    Args:
        path: Path to remove
    """
    try:
        shutil.rmtree(path)
    except OSError as e:
        logging.error(f"Error removing {path}: {e}")

class StubEntry(TypedDict):
    method: Callable[..., Any]
    inCP: bool
    unique: bool

    def __call__( self, generator: 'StubGenerator') -> None:
        if self.inCP:
            assert os.path.exists(generator.circuitpython_dir), "CircuitPython directory does not exist."
            os.chdir(generator.circuitpython_dir)
        else:
            os.chdir(generator.repo_root)
        print(f"Running {self.method.__name__} in {os.getcwd()}")
        self.method(generator)
        

def stubTarget( inCP:bool = True, unique:bool=False  ) :
    def decorate( func: Callable[..., Any] ) -> Callable[..., Any]:
        entry = { 'method':func, 'inCP':inCP, 'unique':unique }
        StubGenerator.targets[func.__name__] = entry
        if not unique:
            StubGenerator.targetsInOrder.append(entry)
        return func
    return decorate

class StubGenerator:
    targets:ClassVar[dict[str,StubEntry]] = {}
    targetsInOrder:ClassVar[list[StubEntry]] = []
    
    def __init__(self, version: str):
        """
        Main function to handle stub generation and management.
        
        Args:
            version: CircuitPython version to checkout
        """
        self.version = version

        # Setup paths
        self.script_dir = Path(__file__).parent.absolute()
        self.repo_root = self.script_dir.parent
        self.circuitpython_dir = self.repo_root / "circuitpython"
        self.venv_dir = self.circuitpython_dir / ".venv"
        self.stubs_dir = self.repo_root / "stubs"
        self.circuitpython_stubs = self.circuitpython_dir / "circuitpython-stubs"

        # Change to repo root
        os.chdir(self.repo_root)
        if os.path.exists(self.venv_dir):
            self._setupVenvCmds()
            
        if os.path.exists(self.circuitpython_dir):
            os.chdir(self.circuitpython_dir)        

    def build(self, target: str) -> None:
        if target not in self.targets:
            logging.error(f"Unknown target: {target}")
            sys.exit(1)
        self.targets[target](self)

    @stubTarget( unique=True )
    def all(self):
        for target in self.targetsInOrder:
            target(self)

    @stubTarget( inCP=False)
    def cloneRepo(self): # Clone repository if it doesn't exist
        if not self.circuitpython_dir.exists():
            os.chdir(self.repo_root)
            self.run_command(f"git clone https://github.com/adafruit/circuitpython.git {self.circuitpython_dir}")
            os.chdir(self.circuitpython_dir)
            
        # Change to circuitpython directory
        os.chdir(self.circuitpython_dir)

        # Checkout specific version and fetch submodules
        self.run_command(f"git checkout {self.version}")
        self.run_command("make fetch-all-submodules")

    @stubTarget()
    def setupVenv(self):
        # Setup virtual environment
        if not os.path.exists(self.venv_dir):
            self.run_command(f"python3 -m venv {self.venv_dir}")

        # Activate virtual environment (Python way)
        assert os.path.exists(self.venv_dir), f"Virtual environment directory {self.venv_dir} does not exist."
        self._setupVenvCmds()
        
        # Install dependencies
        self.run_python("-m pip install --upgrade pip wheel")
        self.run_pip(f"install --upgrade pip wheel")
        self.run_pip(f"install bs4")
        self.run_pip(f"install -r requirements-doc.txt")
        self.run_pip(f"install -r requirements-doc.txt")
        self.run_pip(f"install -r {self.circuitpython_dir}/requirements-doc.txt")

    @stubTarget()
    def makeStubs(self):
        print("GENERATING STUBS...")
        # Generate stubs
        self.run_command(f"make  PYTHON={self.venv_python} stubs")

    @stubTarget()
    def copyStubs(self):

        print("COPYING STUBS...")
        # Handle stubs directory
        if self.stubs_dir.exists():
            safe_rmtree(self.stubs_dir)
        self.stubs_dir.mkdir(parents=True)

        # Move generated stubs
        try:
            for item in self.circuitpython_stubs.glob("*"):
                if item.is_file():
                    shutil.copy2(item, self.stubs_dir)
                else:
                    shutil.copytree(item, self.stubs_dir / item.name)
        except OSError as e:
            logging.error(f"Error copying stubs: {e}")
            sys.exit(1)

    @stubTarget()
    def buildBoards(self):
        print("BUILDING BOARDS...")
        # Change back to repo root and build stubs
        os.chdir(self.repo_root)
        self.run_python(f"./scripts/build-boards.py")

    @stubTarget(unique=True)
    def cleanup(self):
        print("CLEANUP...")
        # Cleanup only the virtual environment
        safe_rmtree(self.venv_dir)

    def _setupVenvCmds(self):
        if os.path.exists(self.venv_dir / "bin"):
            self.venv_pip = self.venv_dir / "bin" / "pip"
            self.venv_python = self.venv_dir / "bin" / "python"
        else:
            self.venv_pip = self.venv_dir / "scripts" / "pip"
            self.venv_python = self.venv_dir / "scripts" / "python"

    def run_pip(self, cmd ):
        self.run_command( f"{self.venv_pip} {cmd}" )

    def run_python(self, cmd):
        self.run_command(f"{self.venv_python} {cmd}")
        
    def run_command(self, cmd: str, cwd: Optional[Path] = None) -> None:
        """
        Execute a shell command and handle errors.
        
        Args:
            cmd: Command to execute
            cwd: Working directory for command execution
        Raises:
            SystemExit: If command execution fails
        """
        logging.debug(f"Executing: {cmd} in {cwd or 'current directory'}")
        try:
            subprocess.run(cmd, cwd=cwd, check=True, shell=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Error executing {cmd}: {e}")
            sys.exit(1)
                    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate and manage CircuitPython stubs.")
    parser.add_argument("target", default="all",
                        choices=StubGenerator.targets.keys(),
                        help=f"stub step (all builds everything except clean in order)")

    parser.add_argument("--version", default=CIRCUITPYTHON_VERSION,
                        help=f"CircuitPython version to checkout (default: {CIRCUITPYTHON_VERSION})")
    
    
    args = parser.parse_args()
    generator = StubGenerator(args.version)
    generator.build(args.target)

# vim: set ts=4 sw=4 tw
