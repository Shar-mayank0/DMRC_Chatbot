import os
from huggingface_hub import snapshot_download
from rich.console import Console
from rich.panel import Panel
from transformers import AutoTokenizer, AutoModel
import gc
import torch
from dotenv import load_dotenv
import torch.version
from accelerate import infer_auto_device_map
from transformers import AutoModelForCausalLM
from accelerate.utils import get_balanced_memory

# Load environment variables from .env file
load_dotenv()

HF_ACCESS_KEY = os.getenv("HF_ACCESS_KEY")
print(f"HF_ACCESS_KEY: {HF_ACCESS_KEY}")
if not HF_ACCESS_KEY:
    raise ValueError("HF_ACCESS_KEY not found in environment variables. Please set it in the .env file.")

cuda_enabled = torch.cuda.is_available()
cuda_device = torch.cuda.current_device() if cuda_enabled else None
cuda_version = torch.version.cuda if cuda_enabled else None



console = Console()

def download_qwen3_embedding_model_gui():
    model_id = "meta-llama/Llama-3.2-3B-Instruct"
    local_dir = os.path.join(os.getcwd(), "models/meta-llama/Llama-3.2-3B-Instruct")

    console.print(Panel.fit(f"[bold cyan]{model_id} Model Downloader[/bold cyan]"))

    console.print("[yellow]Starting model download... please wait.[/yellow]")

    # This will show tqdm in terminal, not rich (but still clean)
    model_dir = snapshot_download(
        token=HF_ACCESS_KEY,
        repo_id=model_id,
        local_dir=local_dir,
    )

    console.print("\n✅ [bold green]Download completed successfully![/bold green]")
    console.print(f"[cyan]Model files saved at:[/cyan] [bold]{model_dir}[/bold]")

    try:
        console.print("\n🔁 [yellow]Verifying tokenizer and model loading...[/yellow]")
        tokenizer = AutoTokenizer.from_pretrained(model_dir , trust_remote_code=True)
        max_memory = {
            0: "6GiB",  # ✅ Key is int (GPU ID), value is str (allowed)
            "cpu": "6GiB"  # ✅ Key is str, value is str — both acceptable
        }

        # First load the model without device mapping
        model = AutoModelForCausalLM.from_pretrained(
            model_dir,
            torch_dtype=torch.bfloat16,
            trust_remote_code=True,
            device_map=None  # Don't map devices yet
        )
        
        # Then infer device map
        device_map = infer_auto_device_map(
            model,
            max_memory=max_memory, # type: ignore
            no_split_module_classes=["LlamaDecoderLayer"]
        )
        
        # Apply the device map using accelerate's dispatch_model
        from accelerate import dispatch_model
        model = dispatch_model(model, device_map=device_map)

        console.print("✅ [green]Model and tokenizer loaded successfully.[/green]")
        del model
        del tokenizer
        torch.cuda.empty_cache()
        gc.collect()
        console.print("🧹 [blue]Model and tokenizer unloaded from RAM.[/blue]")
    except Exception as e:
        console.print(f"❌ [red]Error loading model/tokenizer:[/red] {e}")

    console.print(f"\n📍 [bold]To load locally later:[/bold] [blue]AutoModel.from_pretrained('{model_dir}')[/blue]")

if __name__ == "__main__":
    download_qwen3_embedding_model_gui()
