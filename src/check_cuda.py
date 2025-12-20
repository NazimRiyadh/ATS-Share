import torch 

if torch.cuda.is_available():
    print(f"✅ Success! CUDA is enabled.")
    print(f"   GPU: {torch.cuda.get_device_name(0)}")
    print(f"   VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
    print(f"   CUDA Version: {torch.version.cuda}")
else:
    print("❌ Error: CUDA not detected. Check your install.")