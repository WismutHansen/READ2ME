import yaml
import random
import librosa
import numpy as np
import torch
import torchaudio
from collections import OrderedDict
from munch import Munch
from cached_path import cached_path
from .text_utils import recursive_split

# Local or project imports
from .models import *
from .Utils.PLBERT.util import load_plbert
from .Modules.diffusion.sampler import DiffusionSampler, ADPM2Sampler, KarrasSchedule

# -----------------------------------------------------------------------------
# SEEDS AND DETERMINISM
# -----------------------------------------------------------------------------
random.seed(0)
np.random.seed(0)
torch.manual_seed(0)
torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True

# -----------------------------------------------------------------------------
# CONSTANTS / CHARACTERS
# -----------------------------------------------------------------------------
_pad = "$"
_punctuation = ';:,.!?¡¿—…"«»“” '
_letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
_letters_ipa = "ɑɐɒæɓʙβɔɕçɗɖðʤəɘɚɛɜɝɞɟʄɡɠɢʛɦɧħɥʜɨɪʝɭɬɫɮʟɱɯɰŋɳɲɴøɵɸθœɶʘɹɺɾɻʀʁɽʂʃʈʧʉʊʋⱱʌɣɤʍχʎʏʑʐʒʔʡʕʢǀǁǂǃˈˌːˑʼʴʰʱʲʷˠˤ˞↓↑→↗↘'̩'ᵻ"

symbols = [_pad] + list(_punctuation) + list(_letters) + list(_letters_ipa)

dicts = {symbols[i]: i for i in range(len(symbols))}


# -----------------------------------------------------------------------------
# TEXT CLEANER
# -----------------------------------------------------------------------------
class TextCleaner:
    """
    Maps individual characters to their corresponding indices.
    If an unknown character is found, it prints a warning.
    """

    def __init__(self, dummy=None):
        self.word_index_dictionary = dicts
        print(len(dicts))

    def __call__(self, text):
        indexes = []
        for char in text:
            try:
                indexes.append(self.word_index_dictionary[char])
            except KeyError:
                print("CLEAN", text)
        return indexes


textclenaer = TextCleaner()

# -----------------------------------------------------------------------------
# AUDIO PROCESSING
# -----------------------------------------------------------------------------
to_mel = torchaudio.transforms.MelSpectrogram(
    n_mels=80, n_fft=2048, win_length=1200, hop_length=300
)

mean, std = -4, 4


def preprocess(wave: np.ndarray) -> torch.Tensor:
    """
    Convert a NumPy audio array into a normalized mel spectrogram tensor.
    """
    wave_tensor = torch.from_numpy(wave).float()
    mel_tensor = to_mel(wave_tensor)
    mel_tensor = (torch.log(1e-5 + mel_tensor.unsqueeze(0)) - mean) / std
    return mel_tensor


def length_to_mask(lengths: torch.Tensor) -> torch.Tensor:
    """
    Return a boolean mask based on the lengths of each item in the batch.
    """
    max_len = lengths.max()
    mask = (
        torch.arange(max_len).unsqueeze(0).expand(lengths.shape[0], -1).type_as(lengths)
    )
    mask = torch.gt(mask + 1, lengths.unsqueeze(1))
    return mask


# -----------------------------------------------------------------------------
# MISC UTILS
# -----------------------------------------------------------------------------
def recursive_munch(d):
    """
    Recursively convert dictionaries to Munch objects.
    """
    if isinstance(d, dict):
        return Munch((k, recursive_munch(v)) for k, v in d.items())
    elif isinstance(d, list):
        return [recursive_munch(v) for v in d]
    else:
        return d


def compute_style(path: str) -> torch.Tensor:
    """
    Load an audio file, trim it, resample if needed, then
    compute and return a style vector by passing through the style encoder
    and predictor encoder.
    """
    wave, sr = librosa.load(path, sr=24000)
    audio, _ = librosa.effects.trim(wave, top_db=30)
    if sr != 24000:
        audio = librosa.resample(audio, sr, 24000)

    mel_tensor = preprocess(audio).to(device)
    with torch.no_grad():
        ref_s = model.style_encoder(mel_tensor.unsqueeze(1))
        ref_p = model.predictor_encoder(mel_tensor.unsqueeze(1))

    return torch.cat([ref_s, ref_p], dim=1)


# -----------------------------------------------------------------------------
# DEVICE SELECTION
# -----------------------------------------------------------------------------
device = "cpu"
if torch.cuda.is_available():
    device = "cuda"
elif torch.backends.mps.is_available():
    # Optionally enable MPS if appropriate (commented out by default).
    # device = "mps"
    pass

# -----------------------------------------------------------------------------
# LOAD CONFIG
# -----------------------------------------------------------------------------
config = yaml.safe_load(open("TTS/styletts2_studio/Utils/config.yml"))

# -----------------------------------------------------------------------------
# LOAD MODELS
# -----------------------------------------------------------------------------
ASR_config = config.get("ASR_config", False)
ASR_path = config.get("ASR_path", False)
text_aligner = load_ASR_models(ASR_path, ASR_config)

F0_path = config.get("F0_path", False)
pitch_extractor = load_F0_models(F0_path)

BERT_path = config.get("PLBERT_dir", False)
plbert = load_plbert(BERT_path)

model_params = recursive_munch(config["model_params"])
model = build_model(model_params, text_aligner, pitch_extractor, plbert)
_ = [model[key].eval() for key in model]
_ = [model[key].to(device) for key in model]

params_whole = torch.load(
    str(
        cached_path(
            "hf://yl4579/StyleTTS2-LibriTTS/Models/LibriTTS/epochs_2nd_00020.pth"
        )
    ),
    map_location="cpu",
)
params = params_whole["net"]

# Load model states
for key in model:
    if key in params:
        print(f"{key} loaded")
        try:
            model[key].load_state_dict(params[key])
        except RuntimeError:
            state_dict = params[key]
            new_state_dict = OrderedDict()
            for k, v in state_dict.items():
                name = k[7:]  # remove `module.`
                new_state_dict[name] = v
            model[key].load_state_dict(new_state_dict, strict=False)

_ = [model[key].eval() for key in model]

sampler = DiffusionSampler(
    model.diffusion.diffusion,
    sampler=ADPM2Sampler(),
    sigma_schedule=KarrasSchedule(sigma_min=0.0001, sigma_max=3.0, rho=9.0),
    clamp=False,
)


# -----------------------------------------------------------------------------
# INFERENCE
# -----------------------------------------------------------------------------
def inference(
    text: str,
    ref_s: torch.Tensor,
    alpha: float = 0.3,
    beta: float = 0.7,
    diffusion_steps: int = 5,
    embedding_scale: float = 1,
    speed: float = 1.2,
):
    """
    Perform TTS inference using StyleTTS2 architecture.

    Args:
        text (str): The input text to be synthesized.
        ref_s (torch.Tensor): The reference style/predictor embedding.
        alpha (float): Interpolation factor for the style encoder.
        beta (float): Interpolation factor for the predictor encoder.
        diffusion_steps (int): Number of diffusion steps.
        embedding_scale (float): Scaling factor for the BERT embedding.
        speed (float): Speed factor e.g. 1.2 will speed up the audio by 20%

    Returns:
        np.ndarray: Audio waveform (synthesized speech).
    """
    text = text.strip()

    # Phonemization and Tokenization from Kokoro
    ps = recursive_split(text)  # using tokenization from Kokoro
    ps = " ".join(key for _, key in ps)  # using tokenization from Kokoro

    tokens = textclenaer(ps)
    tokens.insert(0, 0)  # Insert padding index at the start
    tokens = torch.LongTensor(tokens).to(device).unsqueeze(0)

    with torch.no_grad():
        input_lengths = torch.LongTensor([tokens.shape[-1]]).to(device)
        text_mask = length_to_mask(input_lengths).to(device)

        # Text encoder
        t_en = model.text_encoder(tokens, input_lengths, text_mask)

        # BERT duration encoding
        bert_dur = model.bert(tokens, attention_mask=(~text_mask).int())
        d_en = model.bert_encoder(bert_dur).transpose(-1, -2)

        # Sampler for style
        noise = torch.randn((1, 256)).unsqueeze(1).to(device)
        s_pred = sampler(
            noise=noise,
            embedding=bert_dur,
            embedding_scale=embedding_scale,
            features=ref_s,
            num_steps=diffusion_steps,
        ).squeeze(1)

        # Split the style vector
        s_style = s_pred[:, 128:]
        s_ref = s_pred[:, :128]

        # Interpolate with ref_s
        s_ref = alpha * s_ref + (1 - alpha) * ref_s[:, :128]
        s_style = beta * s_style + (1 - beta) * ref_s[:, 128:]

        # Predictor
        d = model.predictor.text_encoder(d_en, s_style, input_lengths, text_mask)
        x, _ = model.predictor.lstm(d)
        duration = model.predictor.duration_proj(x)
        duration = torch.sigmoid(duration).sum(axis=-1)
        duration = duration / speed  # change speed

        # Create alignment
        pred_dur = torch.round(duration.squeeze()).clamp(min=1)
        pred_aln_trg = torch.zeros(input_lengths, int(pred_dur.sum().data))

        c_frame = 0
        for i in range(pred_aln_trg.size(0)):
            pd = int(pred_dur[i].data)
            pred_aln_trg[i, c_frame : c_frame + pd] = 1
            c_frame += pd

        # Encode prosody
        en = d.transpose(-1, -2) @ pred_aln_trg.unsqueeze(0).to(device)
        if model_params.decoder.type == "hifigan":
            asr_new = torch.zeros_like(en)
            asr_new[:, :, 0] = en[:, :, 0]
            asr_new[:, :, 1:] = en[:, :, 0:-1]
            en = asr_new

        F0_pred, N_pred = model.predictor.F0Ntrain(en, s_style)

        # ASR-based encoding
        asr = t_en @ pred_aln_trg.unsqueeze(0).to(device)
        if model_params.decoder.type == "hifigan":
            asr_new = torch.zeros_like(asr)
            asr_new[:, :, 0] = asr[:, :, 0]
            asr_new[:, :, 1:] = asr[:, :, 0:-1]
            asr = asr_new

        out = model.decoder(asr, F0_pred, N_pred, s_ref.squeeze().unsqueeze(0))

    # Return waveform without the last 50 samples (as per original code)
    return out.squeeze().cpu().numpy()[..., :-50]
