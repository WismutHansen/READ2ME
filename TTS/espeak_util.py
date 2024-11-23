import platform
import subprocess
import shutil
from pathlib import Path
import os
from typing import Optional, Tuple
from phonemizer.backend.espeak.wrapper import EspeakWrapper


class EspeakConfig:
    """Utility class for configuring espeak-ng library and binary."""

    @staticmethod
    def find_espeak_binary() -> tuple[bool, Optional[str]]:
        """
        Find espeak-ng binary using multiple methods.

        Returns:
            tuple: (bool indicating if espeak is available, path to espeak binary if found)
        """
        # Common binary names
        binary_names = ["espeak-ng", "espeak"]
        if platform.system() == "Windows":
            binary_names = ["espeak-ng.exe", "espeak.exe"]

        # Common installation directories for Linux
        linux_paths = [
            "/usr/bin",
            "/usr/local/bin",
            "/usr/lib/espeak-ng",
            "/usr/local/lib/espeak-ng",
            "/opt/espeak-ng/bin",
        ]

        # First check if it's in PATH
        for name in binary_names:
            espeak_path = shutil.which(name)
            if espeak_path:
                return True, espeak_path

        # For Linux, check common installation directories
        if platform.system() == "Linux":
            for directory in linux_paths:
                for name in binary_names:
                    path = Path(directory) / name
                    if path.exists():
                        return True, str(path)

        # Try running the command directly as a last resort
        try:
            subprocess.run(
                ["espeak-ng", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            return True, "espeak-ng"
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        return False, None

    @staticmethod
    def find_library_path() -> Optional[str]:
        """
        Find the espeak-ng library using multiple search methods.

        Returns:
            Optional[str]: Path to the library if found, None otherwise
        """
        system = platform.system()

        if system == "Linux":
            lib_names = ["libespeak-ng.so", "libespeak-ng.so.1"]
            common_paths = [
                # Debian/Ubuntu paths
                "/usr/lib/x86_64-linux-gnu",
                "/usr/lib/aarch64-linux-gnu",  # For ARM64
                "/usr/lib/arm-linux-gnueabihf",  # For ARM32
                "/usr/lib",
                "/usr/local/lib",
                # Fedora/RHEL paths
                "/usr/lib64",
                "/usr/lib32",
                # Common additional paths
                "/usr/lib/espeak-ng",
                "/usr/local/lib/espeak-ng",
                "/opt/espeak-ng/lib",
            ]

            # Check common locations first
            for path in common_paths:
                for lib_name in lib_names:
                    lib_path = Path(path) / lib_name
                    if lib_path.exists():
                        return str(lib_path)

            # Search system library paths
            try:
                # Use ldconfig to find the library
                result = subprocess.run(
                    ["ldconfig", "-p"], capture_output=True, text=True, check=True
                )
                for line in result.stdout.splitlines():
                    if "libespeak-ng.so" in line:
                        # Extract path from ldconfig output
                        return line.split("=>")[-1].strip()
            except (subprocess.SubprocessError, FileNotFoundError):
                pass

        elif system == "Darwin":  # macOS
            common_paths = [
                Path("/opt/homebrew/lib/libespeak-ng.dylib"),
                Path("/usr/local/lib/libespeak-ng.dylib"),
                *list(
                    Path("/opt/homebrew/Cellar/espeak-ng").glob(
                        "*/lib/libespeak-ng.dylib"
                    )
                ),
                *list(
                    Path("/usr/local/Cellar/espeak-ng").glob("*/lib/libespeak-ng.dylib")
                ),
            ]

            for path in common_paths:
                if path.exists():
                    return str(path)

        elif system == "Windows":
            common_paths = [
                Path(os.environ.get("PROGRAMFILES", "C:\\Program Files"))
                / "eSpeak NG"
                / "libespeak-ng.dll",
                Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"))
                / "eSpeak NG"
                / "libespeak-ng.dll",
                *[
                    Path(p) / "libespeak-ng.dll"
                    for p in os.environ.get("PATH", "").split(os.pathsep)
                ],
            ]

            for path in common_paths:
                if path.exists():
                    return str(path)

        return None

    @classmethod
    def configure_espeak(cls) -> Tuple[bool, str]:
        """
        Configure espeak-ng for use with the phonemizer.

        Returns:
            Tuple[bool, str]: (Success status, Status message)
        """
        # First check if espeak binary is available
        espeak_available, espeak_path = cls.find_espeak_binary()
        if not espeak_available:
            raise FileNotFoundError(
                "Could not find espeak-ng binary. Please install espeak-ng:\n"
                "Ubuntu/Debian: sudo apt-get install espeak-ng espeak-ng-data\n"
                "Fedora: sudo dnf install espeak-ng\n"
                "Arch: sudo pacman -S espeak-ng\n"
                "MacOS: brew install espeak-ng\n"
                "Windows: Download from https://github.com/espeak-ng/espeak-ng/releases"
            )

        # Find the library
        library_path = cls.find_library_path()
        if not library_path:
            # On Linux, we might not need to explicitly set the library path
            if platform.system() == "Linux":
                return True, f"Using system espeak-ng installation at: {espeak_path}"
            else:
                raise FileNotFoundError(
                    "Could not find espeak-ng library. Please ensure espeak-ng is properly installed."
                )

        # Try to set the library path
        try:
            EspeakWrapper.set_library(library_path)
            return True, f"Successfully configured espeak-ng library at: {library_path}"
        except Exception as e:
            if platform.system() == "Linux":
                # On Linux, try to continue without explicit library path
                return True, f"Using system espeak-ng installation at: {espeak_path}"
            else:
                raise RuntimeError(f"Failed to configure espeak-ng library: {str(e)}")


def setup_espeak():
    """
    Set up espeak-ng for use with the phonemizer.
    Raises appropriate exceptions if setup fails.
    """
    try:
        success, message = EspeakConfig.configure_espeak()
        print(message)
    except Exception as e:
        print(f"Error configuring espeak-ng: {str(e)}")
        raise


# Replace the original set_espeak_library function with this
set_espeak_library = setup_espeak
