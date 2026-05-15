import os
import warnings
import logging

# Disable download progress bars.
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

os.environ["HF_HUB_VERBOSITY"] = "error"   
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

# Suppress common CUDA and authentication warnings.
warnings.filterwarnings("ignore", category=UserWarning, message=".*CUDA initialization.*")
warnings.filterwarnings("ignore", message=".*unauthenticated requests.*")

from engine.logger import logger

logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)

from sentence_transformers import SentenceTransformer, util

CATEGORY_DESCRIPTIONS = {
    "Internet Browsers": "A web browser for navigating the internet, rendering HTML pages, managing bookmarks and tabs, browsing websites",
    "Productivity Tools": "Office suite, document editor, spreadsheet, task manager, note-taking, writing tool, calendar, PDF editor, AI writing assistant, project management, ChatGPT, Claude, AI tools",
    "Communication & Collaboration": (
        "Messaging app, email client, video conferencing, team chat, voice calls, "
        "social networking, workplace communication, business messaging, instant messaging, "
        "group chat, channels, direct messages, Slack, Teams, Discord"
    ),
    "Out-of-browser Entertainment": (
        "Multimedia player, media player software, video player, audio player, "
        "movie and music streaming, broadcasting, video game, game launcher, "
        "gaming platform, emulation"
    ),
    "Utilities & Maintenance": "System utility, operating system, linux distro, wsl, antivirus, VPN, disk cleaner, driver manager, file manager, system optimization",
    "Media Creation": (
        "Photo editor, image editor, image manipulation program, video editor, audio editor, "
        "3D modeling, graphic design, illustration, animation tool, drawing, painting, "
        "raster graphics, vector graphics, digital art creation"
    ),
    "Development & Programming": (
        "Code editor, IDE, compiler, terminal, version control, API client, "
        "developer framework, programming tool, repository, precompiled binaries, "
        "linux server, wsl environment"
    ),
    "Others": "Uncategorized or general purpose application",
}

CONFIDENCE_THRESHOLD = 0.25
MODEL_NAME = "all-MiniLM-L6-v2"
LOCAL_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_model")

class EmbeddingClassifier:
    @staticmethod
    def need_download() -> bool:
        return not os.path.exists(LOCAL_MODEL_PATH)
    
    def __init__(self):
        # Check whether the local model is already available.
        if self.need_download():
            logger.info(f"Model not found locally in {LOCAL_MODEL_PATH}")
            logger.info(f"Downloading '{MODEL_NAME}'... (one-time operation)")
            
            # Download and cache the model on first use.
            temp_model = SentenceTransformer(MODEL_NAME)
            temp_model.save(LOCAL_MODEL_PATH)
            
            logger.info("Model saved successfully in the local directory.")

        # Load the cached local model.
        self.model = SentenceTransformer(LOCAL_MODEL_PATH)

        self.category_embeddings = {
            cat: self.model.encode(desc)
            for cat, desc in CATEGORY_DESCRIPTIONS.items()
            if cat != "Others" 
        }

    def classify(self, tokens: list[str]) -> str:
        app_text = " ".join(t for t in tokens if t.strip())

        if not app_text:
            return "Others"

        app_embedding = self.model.encode(app_text)

        scores = {
            cat: util.cos_sim(app_embedding, emb).item()
            for cat, emb in self.category_embeddings.items()
        }

        best_category = max(scores, key=scores.get)
        best_score = scores[best_category]

        return best_category if best_score >= CONFIDENCE_THRESHOLD else "Others"
