import subprocess
import logging
import asyncio
from fastapi import FastAPI, HTTPException
import os


async def pdf2markdown(pdfpath, output_path="Output"):
    try:
        os.environ['EXTRACT_IMAGES'] = 'false'
        
        command = [
            "marker_single",
            pdfpath,
            output_path,
            "--batch_multiplier=4",
        ]
        process = await asyncio.create_subprocess_exec(
        *command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            logging.info("PDF converted into markdown")
            return True
        else:
            logging.error(f"Failed to convert PDF to markdown: {stderr.decode()}")
            return False

    except Exception as e:
        logging.error(f"Exception occurred: {e}")
        return False

if __name__ == "__main__":
    pdf = input("Enter the path of the PDF file to be converted: ")
    asyncio.run(pdf2markdown(pdf))    

