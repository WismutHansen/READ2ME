import torch
import numpy as np
import queue
from typing import Optional, Generator, Tuple
from tools.api import decode_vq_tokens
from tools.llama.generate import (
    GenerateRequest,
    GenerateResponse,
    WrappedGenerateResponse,
)


@torch.inference_mode()
def inference(
    text: str,
    enable_reference_audio: bool = False,
    reference_audio: Optional[np.ndarray] = None,
    reference_text: str = "",
    max_new_tokens: int = 200,
    chunk_length: int = 200,
    top_p: float = 0.7,
    repetition_penalty: float = 1.2,
    temperature: float = 0.7,
    seed: str = "0",
    prompt_tokens: Optional[np.ndarray] = None,
) -> Generator[
    Tuple[Optional[bytes], Tuple[int, np.ndarray], Optional[str]], None, None
]:
    """
    Perform inference using Fish TTS.
    """
    if int(seed) != 0:
        torch.manual_seed(int(seed))

    request = dict(
        device="cuda" if torch.cuda.is_available() else "cpu",
        max_new_tokens=max_new_tokens,
        text=text,
        top_p=top_p,
        repetition_penalty=repetition_penalty,
        temperature=temperature,
        iterative_prompt=chunk_length > 0,
        chunk_length=chunk_length,
        max_length=2048,
        prompt_tokens=prompt_tokens if enable_reference_audio else None,
        prompt_text=reference_text if enable_reference_audio else None,
    )

    response_queue = queue.Queue()
    llama_queue.put(
        GenerateRequest(
            request=request,
            response_queue=response_queue,
        )
    )

    segments = []

    while True:
        result: WrappedGenerateResponse = response_queue.get()
        if result.status == "error":
            yield None, None, f"Error in inference: {result.response}"
            break

        result: GenerateResponse = result.response
        if result.action == "next":
            break

        fake_audios = decode_vq_tokens(
            decoder_model=decoder_model,
            codes=result.codes,
        )

        fake_audios = fake_audios.float().cpu().numpy()
        segments.append(fake_audios)

    # Concatenate all audio segments and return
    if len(segments) == 0:
        yield None, None, "No audio generated"
    else:
        audio = np.concatenate(segments, axis=0)
        yield None, (24000, audio), None  # Assume a 24 kHz sample rate
