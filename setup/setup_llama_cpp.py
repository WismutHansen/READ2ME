import subprocess
import sys
import os
import platform
import ctypes.util


def detect_hardware():
    """Detect available GPU hardware and OS type."""
    try:
        import torch

        if torch.cuda.is_available():
            cuda_version = torch.__version__.__dict__.get("cuda", None)
            return "CUDA", cuda_version
    except ImportError:
        pass

    # Check for AMD ROCm
    if os.environ.get("ROCR_VISIBLE_DEVICES"):
        return "ROCm", None

    # macOS-specific check for Metal support
    if platform.system() == "Darwin":
        try:
            metal = ctypes.util.find_library("Metal")
            if metal:
                return "Metal", None
        except Exception:
            pass

    # Check Vulkan environment variable (common on Linux/Windows)
    if os.environ.get("VK_ICD_FILENAMES"):
        return "Vulkan", None

    return "CPU", None


def install_llama_cpp():
    """Install llama-cpp-python with appropriate GPU or CPU support."""
    backend, version = detect_hardware()

    if backend == "CUDA":
        # Use CUDA pre-built wheel
        major_minor = version.split(".")[:2] if version else ["0", "0"]
        version_tag = f"cu{''.join(major_minor)}"
        index_url = f"https://abetlen.github.io/llama-cpp-python/whl/{version_tag}"
        install_command = [
            sys.executable,
            "-m",
            "pip",
            "install",
            f"llama-cpp-python --extra-index-url {index_url}",
        ]
    elif backend == "ROCm":
        # ROCm backend
        install_command = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "llama-cpp-python",
            "-C",
            "GGML_HIP=on",
        ]
    elif backend == "Metal":
        # Metal backend for macOS
        install_command = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "llama-cpp-python",
            "-C",
            "GGML_METAL=on",
        ]
    elif backend == "Vulkan":
        # Vulkan backend
        install_command = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "llama-cpp-python",
            "-C",
            "GGML_VULKAN=on",
        ]
    else:
        # CPU backend
        install_command = [sys.executable, "-m", "pip", "install", "llama-cpp-python"]

    print(f"Installing llama-cpp-python with {backend} support...")
    try:
        subprocess.check_call(install_command, shell=True)
        print("llama-cpp-python installed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Installation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    install_llama_cpp()
