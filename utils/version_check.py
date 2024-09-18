# File: utils/version_check.py

import pkg_resources
import logging
from pathlib import Path

def check_package_versions():
    logging.info("Checking package versions...")
    
    requirements_files = [
        Path(__file__).parent.parent / "requirements.txt",
        Path(__file__).parent.parent / "requirements_stts2.txt"
    ]
    
    all_requirements = []
    for req_file in requirements_files:
        with open(req_file, 'r') as f:
            all_requirements.extend(f.readlines())
    
    results = []
    for req in all_requirements:
        req = req.strip()
        if req and not req.startswith('#') and not req.startswith('git+'):
            try:
                package_name = req.split('==')[0] if '==' in req else req
                installed_version = pkg_resources.get_distribution(package_name).version
                if '==' in req:
                    required_version = req.split('==')[1]
                    if installed_version != required_version:
                        results.append(f"Warning: {package_name} version mismatch. Required: {required_version}, Installed: {installed_version}")
                    else:
                        results.append(f"OK: {package_name} version {installed_version}")
                else:
                    results.append(f"Info: {package_name} version {installed_version} (no specific version required)")
            except pkg_resources.DistributionNotFound:
                results.append(f"Error: {package_name} is not installed")
    
    # Log and write results to a file
    log_file = Path(__file__).parent.parent / "package_versions.log"
    with open(log_file, 'w') as f:
        for result in results:
            logging.info(result)
            f.write(result + '\n')
    
    logging.info(f"Package version check complete. Results written to {log_file}")

# Call this function at the start of your main script
if __name__ == "__main__":
    check_package_versions()