from cached_path import cached_path
import os
import inspect

import subprocess
from typing import Optional
import shutil
from pathlib import Path

import torch

torch.manual_seed(0)
torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True

import random

random.seed(0)

import numpy as np

np.random.seed(0)

import nltk

nltk.download("punkt")
nltk.download("punkt_tab")

# load packages
import random
import yaml
import numpy as np
import torch
import torchaudio
import librosa
from nltk.tokenize import word_tokenize

from .models import *
from .utils import *
from .text_utils import TextCleaner

textclenaer = TextCleaner()

# Define the cache directory
cache_dir = "TTS/styletts2/Models/"
os.makedirs(cache_dir, exist_ok=True)

# Get the file path of the current module
module_file = inspect.getfile(inspect.currentframe())

# Get the directory of the current module
module_dir = os.path.dirname(module_file)

device = "cuda" if torch.cuda.is_available() else "cpu"

to_mel = torchaudio.transforms.MelSpectrogram(
    n_mels=80, n_fft=2048, win_length=1200, hop_length=300
)
mean, std = -4, 4


def length_to_mask(lengths):
    mask = (
        torch.arange(lengths.max())
        .unsqueeze(0)
        .expand(lengths.shape[0], -1)
        .type_as(lengths)
    )
    mask = torch.gt(mask + 1, lengths.unsqueeze(1))
    return mask


def preprocess(wave):
    wave_tensor = torch.from_numpy(wave).float()
    mel_tensor = to_mel(wave_tensor)
    mel_tensor = (torch.log(1e-5 + mel_tensor.unsqueeze(0)) - mean) / std
    return mel_tensor


def compute_style(ref_dicts):
    reference_embeddings = {}
    for key, path in ref_dicts.items():
        wave, sr = librosa.load(path, sr=24000)
        audio, index = librosa.effects.trim(wave, top_db=30)
        if sr != 24000:
            audio = librosa.resample(audio, sr, 24000)
        mel_tensor = preprocess(audio).to(device)

        with torch.no_grad():
            ref = model.style_encoder(mel_tensor.unsqueeze(1))
        reference_embeddings[key] = (ref.squeeze(1), audio)

    return reference_embeddings


# load phonemizer
import phonemizer
from phonemizer.backend.espeak.wrapper import EspeakWrapper

# if windows set espeakwrapper
import platform


def check_espeak_availability() -> tuple[bool, Optional[str]]:
    """
    Check if espeak-ng is available on the system PATH.

    Returns:
        tuple: (bool indicating if espeak is available, path to espeak binary if found)
    """
    # First check if the command is available on PATH
    espeak_binary = "espeak-ng.exe" if platform.system() == "Windows" else "espeak-ng"
    espeak_path = shutil.which(espeak_binary)

    if espeak_path:
        return True, espeak_path

    # If not found directly, try running the command to see if it's accessible
    try:
        subprocess.run(
            ["espeak-ng", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        return True, None
    except (subprocess.SubprocessError, FileNotFoundError):
        return False, None


def find_library_path() -> Optional[str]:
    """
    Find the espeak-ng library path based on the OS and common installation locations.

    Returns:
        Optional[str]: Path to the library if found, None otherwise
    """
    if platform.system() == "Windows":
        common_paths = [
            Path(os.environ.get("PROGRAMFILES", "C:\\Program Files"))
            / "eSpeak NG"
            / "libespeak-ng.dll",
            Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"))
            / "eSpeak NG"
            / "libespeak-ng.dll",
            # Check for custom installation in PATH directories
            *[
                Path(p) / "libespeak-ng.dll"
                for p in os.environ.get("PATH", "").split(os.pathsep)
            ],
        ]
        lib_name = "libespeak-ng.dll"
    elif platform.system() == "Darwin":  # macOS
        common_paths = [
            Path("/opt/homebrew/Cellar/espeak-ng/1.51/lib/libespeak-ng.dylib"),
            Path("/usr/local/lib/libespeak-ng.dylib"),
            Path("/opt/homebrew/lib/libespeak-ng.dylib"),
            # Additional Homebrew paths
            *list(
                Path("/opt/homebrew/Cellar/espeak-ng").glob("*/lib/libespeak-ng.dylib")
            ),
            *list(Path("/usr/local/Cellar/espeak-ng").glob("*/lib/libespeak-ng.dylib")),
        ]
        lib_name = "libespeak-ng.dylib"
    elif platform.system() == "Linux":
        common_paths = [
            Path("/usr/lib/libespeak-ng.so"),
            Path("/usr/local/lib/libespeak-ng.so"),
            Path("/usr/lib/x86_64-linux-gnu/libespeak-ng.so"),  # Debian/Ubuntu
            Path("/usr/lib64/libespeak-ng.so"),  # Fedora/RHEL
            Path("/usr/bin/espeak-ng/libespeak-ng.so"),
        ]
        lib_name = "libespeak-ng.so"
    else:
        raise EnvironmentError(f"Unsupported operating system: {platform.system()}")

    # Check all common paths
    for path in common_paths:
        if path.exists():
            return str(path)

    # If not found in common paths, try to find it in system library paths
    system_lib_paths = [
        p.strip()
        for p in os.environ.get("LD_LIBRARY_PATH", "").split(os.pathsep)
        + os.environ.get("DYLD_LIBRARY_PATH", "").split(os.pathsep)
        + os.environ.get("PATH", "").split(os.pathsep)
        if p.strip()
    ]

    for lib_path in system_lib_paths:
        path = Path(lib_path) / lib_name
        if path.exists():
            return str(path)

    return None


def set_espeak_library():
    """
    Configure the espeak-ng library for use with the wrapper.
    First checks if espeak-ng is available on PATH, then searches for the library in common locations.

    Raises:
        FileNotFoundError: If the espeak-ng library cannot be found
        EnvironmentError: If running on an unsupported OS
    """
    # First check if espeak is available on the system
    espeak_available, espeak_path = check_espeak_availability()

    if espeak_available:
        print(f"Found espeak-ng on system: {espeak_path or 'available in PATH'}")

        # If espeak is available, try to find the library
        library_path = find_library_path()
        if library_path:
            try:
                EspeakWrapper.set_library(library_path)
                print(f"Successfully configured eSpeak-NG library at: {library_path}")
                return
            except Exception as e:
                print(
                    f"Warning: Found library at {library_path} but failed to load it: {e}"
                )
                # Continue to try other methods if this fails

    # If we reach here, we couldn't find or load the library
    raise FileNotFoundError(
        "Could not find or load eSpeak-NG library. Please ensure espeak-ng is installed.\n"
        f"Installation guide for {platform.system()}:\n"
        "Windows: Download from https://github.com/espeak-ng/espeak-ng/releases\n"
        "MacOS: brew install espeak-ng\n"
        "Linux: sudo apt-get install espeak-ng-data libespeak-ng1 (Ubuntu/Debian)\n"
        "       sudo dnf install espeak-ng (Fedora)\n"
        "       sudo pacman -S espeak-ng (Arch)"
    )


set_espeak_library()

global_phonemizer = phonemizer.backend.EspeakBackend(
    language="en-us",
    preserve_punctuation=True,
    with_stress=True,
    words_mismatch="ignore",
)

# phonemizer = Phonemizer.from_checkpoint(str(cached_path('https://public-asai-dl-models.s3.eu-central-1.amazonaws.com/DeepPhonemizer/en_us_cmudict_ipa_forward.pt')))

# check if Model folder and model files exist else download it or use cache

config = yaml.safe_load(
    open(
        str(
            cached_path(
                "hf://yl4579/StyleTTS2-LJSpeech/Models/LJSpeech/config.yml",
                cache_dir=cache_dir,
            )
        )
    )
)

# load pretrained ASR model
ASR_config = config.get("ASR_config", False)
ASR_path = os.path.join(module_dir, config.get("ASR_path", False))
text_aligner = load_ASR_models(ASR_path, ASR_config)

# load pretrained F0 model
F0_path = os.path.join(module_dir, config.get("F0_path", False))
pitch_extractor = load_F0_models(F0_path)

# load BERT model
from .Utils.PLBERT.util import load_plbert

BERT_path = os.path.join(module_dir, config.get("PLBERT_dir", False))
plbert = load_plbert(BERT_path)

model = build_model(
    recursive_munch(config["model_params"]), text_aligner, pitch_extractor, plbert
)
_ = [model[key].eval() for key in model]
_ = [model[key].to(device) for key in model]

params_whole = torch.load(
    str(
        cached_path(
            "hf://yl4579/StyleTTS2-LJSpeech/Models/LJSpeech/epoch_2nd_00100.pth",
            cache_dir=cache_dir,
        )
    ),
    map_location="cpu",
)
params = params_whole["net"]

for key in model:
    if key in params:
        print("%s loaded" % key)
        try:
            model[key].load_state_dict(params[key])
        except:
            from collections import OrderedDict

            state_dict = params[key]
            new_state_dict = OrderedDict()
            for k, v in state_dict.items():
                name = k[7:]  # remove `module.`
                new_state_dict[name] = v
            # load params
            model[key].load_state_dict(new_state_dict, strict=False)
#             except:
#                 _load(params[key], model[key])
_ = [model[key].eval() for key in model]

from .Modules.diffusion.sampler import DiffusionSampler, ADPM2Sampler, KarrasSchedule

sampler = DiffusionSampler(
    model.diffusion.diffusion,
    sampler=ADPM2Sampler(),
    sigma_schedule=KarrasSchedule(
        sigma_min=0.0001, sigma_max=3.0, rho=9.0
    ),  # empirical parameters
    clamp=False,
)


def inference(text, noise, diffusion_steps=5, embedding_scale=1):
    text = text.strip()
    text = text.replace('"', "")
    ps = global_phonemizer.phonemize([text])
    ps = word_tokenize(ps[0])
    ps = " ".join(ps)

    tokens = textclenaer(ps)
    tokens.insert(0, 0)

    # Truncate tokens to the maximum sequence length allowed by the model
    max_seq_length = 512
    tokens = tokens[:max_seq_length]

    tokens = torch.LongTensor(tokens).to(device).unsqueeze(0)

    with torch.no_grad():
        input_lengths = torch.LongTensor([tokens.shape[-1]]).to(tokens.device)
        text_mask = length_to_mask(input_lengths).to(tokens.device)

        t_en = model.text_encoder(tokens, input_lengths, text_mask)
        bert_dur = model.bert(tokens, attention_mask=(~text_mask).int())
        d_en = model.bert_encoder(bert_dur).transpose(-1, -2)

        s_pred = sampler(
            noise,
            embedding=bert_dur[0].unsqueeze(0),
            num_steps=diffusion_steps,
            embedding_scale=embedding_scale,
        ).squeeze(0)

        s = s_pred[:, 128:]
        ref = s_pred[:, :128]

        d = model.predictor.text_encoder(d_en, s, input_lengths, text_mask)

        x, _ = model.predictor.lstm(d)
        duration = model.predictor.duration_proj(x)
        duration = (
            torch.sigmoid(duration).sum(axis=-1) / 1.3
        )  # adjust speed by dividing through a number e.g. 1.25 = 25& faster
        pred_dur = torch.round(duration.squeeze()).clamp(min=1)

        pred_dur[-1] += 5

        pred_aln_trg = torch.zeros(input_lengths, int(pred_dur.sum().data))
        c_frame = 0
        for i in range(pred_aln_trg.size(0)):
            pred_aln_trg[i, c_frame : c_frame + int(pred_dur[i].data)] = 1
            c_frame += int(pred_dur[i].data)

        # encode prosody
        en = d.transpose(-1, -2) @ pred_aln_trg.unsqueeze(0).to(device)
        F0_pred, N_pred = model.predictor.F0Ntrain(en, s)
        out = model.decoder(
            (t_en @ pred_aln_trg.unsqueeze(0).to(device)),
            F0_pred,
            N_pred,
            ref.squeeze().unsqueeze(0),
        )

    return out.squeeze().cpu().numpy()


def LFinference(text, s_prev, noise, alpha=0.7, diffusion_steps=5, embedding_scale=1):
    text = text.strip()
    text = text.replace('"', "")
    ps = global_phonemizer.phonemize([text])
    ps = word_tokenize(ps[0])
    ps = " ".join(ps)

    tokens = textclenaer(ps)
    tokens.insert(0, 0)
    tokens = torch.LongTensor(tokens).to(device).unsqueeze(0)

    with torch.no_grad():
        input_lengths = torch.LongTensor([tokens.shape[-1]]).to(tokens.device)
        text_mask = length_to_mask(input_lengths).to(tokens.device)

        t_en = model.text_encoder(tokens, input_lengths, text_mask)
        bert_dur = model.bert(tokens, attention_mask=(~text_mask).int())
        d_en = model.bert_encoder(bert_dur).transpose(-1, -2)

        s_pred = sampler(
            noise,
            embedding=bert_dur[0].unsqueeze(0),
            num_steps=diffusion_steps,
            embedding_scale=embedding_scale,
        ).squeeze(0)

        if s_prev is not None:
            # convex combination of previous and current style
            s_pred = alpha * s_prev + (1 - alpha) * s_pred

        s = s_pred[:, 128:]
        ref = s_pred[:, :128]

        d = model.predictor.text_encoder(d_en, s, input_lengths, text_mask)

        x, _ = model.predictor.lstm(d)
        duration = model.predictor.duration_proj(x)
        duration = torch.sigmoid(duration).sum(axis=-1)
        pred_dur = torch.round(duration.squeeze()).clamp(min=1)

        pred_aln_trg = torch.zeros(input_lengths, int(pred_dur.sum().data))
        c_frame = 0
        for i in range(pred_aln_trg.size(0)):
            pred_aln_trg[i, c_frame : c_frame + int(pred_dur[i].data)] = 1
            c_frame += int(pred_dur[i].data)

        # encode prosody
        en = d.transpose(-1, -2) @ pred_aln_trg.unsqueeze(0).to(device)
        F0_pred, N_pred = model.predictor.F0Ntrain(en, s)
        out = model.decoder(
            (t_en @ pred_aln_trg.unsqueeze(0).to(device)),
            F0_pred,
            N_pred,
            ref.squeeze().unsqueeze(0),
        )

    return out.squeeze().cpu().numpy(), s_pred
