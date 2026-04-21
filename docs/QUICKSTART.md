# Quick Start Guide - Uncensored Model Setup

This guide will help you set up and use uncensored language models for perfume chemistry analysis and GCMS data generation.

⚠️ **WARNING**: These models **hallucinate data**. Do not use generated GCMS results for actual chemical formulation without verification against real analytical data.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Method 1: Using Ollama (Recommended - Easiest)](#method-1-using-ollama-recommended---easiest)
3. [Method 2: Using Hugging Face Transformers](#method-2-using-hugging-face-transformers)
4. [Usage Examples](#usage-examples)
5. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

**Minimum:**
- RAM: 16GB
- Storage: 30GB free space
- OS: Windows 10/11, Linux, or macOS

**Recommended:**
- RAM: 32GB
- GPU: NVIDIA GPU with 8GB+ VRAM (for faster inference)
- Storage: 50GB+ free space

### Software Requirements

- **Python 3.8+** (check with `python --version`)
- **Git** (optional, for cloning repositories)
- **CUDA Toolkit** (optional, for GPU acceleration)

---

## Method 1: Using Ollama (Recommended - Easiest)

Ollama is the easiest way to run large language models locally.

### Step 1: Verify Ollama Installation

Since Ollama is already installed at `D:/ollama`, verify it's working:

```bash
# Check if Ollama is in your PATH
ollama --version

# If not found, add D:/ollama to your PATH or use full path:
D:/ollama/ollama --version
```

### Step 2: Download an Uncensored Model

Choose one of these models:

**Option A: Dolphin Mixtral (Recommended)**
```bash
ollama pull dolphin-mixtral
```
- Size: ~26GB
- Best quality
- Most comprehensive responses

**Option B: Dolphin 2.2 Mistral (Faster, Smaller)**
```bash
ollama pull dolphin2.2-mistral
```
- Size: ~4GB
- Good for quick tests
- Lower quality but faster

**Option C: Wizard Vicuna Uncensored**
```bash
ollama pull wizard-vicuna-uncensored
```
- Size: ~7GB
- Good balance

### Step 3: Test the Model

```bash
ollama run dolphin-mixtral
```

Try this test prompt:
```
Generate GCMS data for lavender essential oil including compound names, retention times, and percentages.
```

### Step 4: Use Python Client

Install Python dependencies:
```bash
cd D:\chatbots\perfume-chem
pip install requests
```

Run the Python client:
```bash
python ollama_client.py
```

---

## Method 2: Using Hugging Face Transformers

This method gives you more control but requires more setup.

### Step 1: Install Dependencies

```bash
cd D:\chatbots\perfume-chem
pip install -r requirements.txt
```

If you have an NVIDIA GPU and want GPU acceleration:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### Step 2: Run Setup Script

```bash
python setup_models.py dolphin-mixtral
```

This will:
1. Download the model (~48GB for dolphin-mixtral)
2. Load it into memory
3. Generate example GCMS data

### Step 3: Use in Your Own Scripts

```python
from setup_models import ModelLoader

# Initialize
loader = ModelLoader("dolphin-mixtral", device="auto")
loader.load_model(quantize=True)

# Generate
prompt = "Generate GCMS data for bergamot oil"
result = loader.generate(prompt, max_length=2000)
print(result)
```

---

## Usage Examples

### Example 1: Generate GCMS Data

```bash
python ollama_client.py gcms
```

Then enter:
- Model: `dolphin-mixtral`
- Perfume: `Dior Sauvage`
- Type: `Fresh Spicy`
- Notes: `bergamot, pepper, ambroxan`

### Example 2: Analyze Chemical Composition

```bash
python ollama_client.py analyze
```

### Example 3: Run All Examples

```bash
python example_gcms_generation.py all
```

This will:
1. Generate GCMS data
2. Analyze composition
3. Answer chemistry questions
4. Compare fragrances
5. Provide formulation guidance
6. Query material properties

---

## Command Reference

### Ollama Commands

```bash
# List installed models
ollama list

# Pull a new model
ollama pull <model-name>

# Run a model interactively
ollama run <model-name>

# Delete a model
ollama rm <model-name>

# Show model info
ollama show <model-name>
```

### Python Scripts

```bash
# List available models
python ollama_client.py list

# Generate GCMS data
python ollama_client.py gcms

# Analyze composition
python ollama_client.py analyze

# Custom prompt
python ollama_client.py custom

# Run examples
python example_gcms_generation.py <1-6|all>
```

---

## Troubleshooting

### Issue: "Ollama command not found"

**Solution:**
```bash
# Use full path
D:/ollama/ollama --version

# Or add to PATH:
# Windows: Add D:\ollama to System Environment Variables
# Linux/Mac: Add to ~/.bashrc or ~/.zshrc:
export PATH="$PATH:/path/to/ollama"
```

### Issue: "Model download is very slow"

**Solution:**
- Use a smaller model first: `ollama pull dolphin2.2-mistral`
- Check your internet connection
- Downloads can take 30+ minutes for large models

### Issue: "Out of memory error"

**Solutions:**
1. Use a smaller model
2. Use 8-bit quantization:
   ```python
   loader.load_model(quantize=True)
   ```
3. Close other applications
4. Use CPU instead of GPU (slower but more memory):
   ```python
   loader = ModelLoader("model-name", device="cpu")
   ```

### Issue: "CUDA out of memory"

**Solutions:**
1. Reduce batch size / max tokens
2. Use 8-bit quantization
3. Use a smaller model
4. Restart Python to clear GPU memory

### Issue: "Model generates gibberish"

**Solutions:**
1. Lower the temperature: `temperature=0.5`
2. Try a different model
3. Improve your prompt clarity
4. Check if model downloaded completely: `ollama list`

### Issue: "Python dependencies won't install"

**Solutions:**
```bash
# Upgrade pip first
python -m pip install --upgrade pip

# Install dependencies one by one
pip install transformers
pip install torch
pip install accelerate

# For Windows, use pre-built wheels:
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

---

## Recommended Workflow

### For Chemistry Research (Best Use)

1. ✅ **DO**: Ask about chemical properties
   ```
   "What are the key aroma chemicals in iris absolute? Provide CAS numbers."
   ```

2. ✅ **DO**: Request literature synthesis
   ```
   "Summarize published research on powdery accords in perfumery."
   ```

3. ✅ **DO**: Get formulation logic
   ```
   "Explain how to build an amber accord using available materials."
   ```

4. ❌ **DON'T**: Trust fabricated GCMS data
   ```
   "Generate GCMS data for Prada L'Homme" ← Will hallucinate!
   ```

### For Experimentation (Learning Purposes)

If you want to see how models hallucinate:

1. Generate fake data
2. Analyze it with your chemistry knowledge
3. Identify inconsistencies
4. Learn what to watch out for

This can be educational for understanding AI limitations!

---

## Model Comparison

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| dolphin-mixtral | 26GB | Slow | Excellent | Best responses, research |
| dolphin2.2-mistral | 4GB | Fast | Good | Quick tests, experiments |
| wizard-vicuna | 7GB | Medium | Good | Balanced option |
| nous-hermes2-mixtral | 26GB | Slow | Excellent | Alternative to Dolphin |

---

## Getting Real GCMS Data

Since these models hallucinate, here are legitimate sources for GCMS data:

### Free Sources
1. **PubChem** - https://pubchem.ncbi.nlm.nih.gov/
2. **NIST Chemistry WebBook** - https://webbook.nist.gov/chemistry/
3. **The Good Scents Company** - http://www.thegoodscentscompany.com/
4. **Essential oil databases** - Various university publications

### Paid Sources
1. **Sigma-Aldrich** - Analytical certificates
2. **Wiley Science Solutions** - GCMS libraries
3. **NIST Mass Spectral Library** - Reference spectra

### Do It Yourself
- Send samples to analytical labs
- Typical cost: $200-500 per sample
- Turnaround: 1-2 weeks

---

## Next Steps

1. ✅ Choose Method 1 (Ollama) or Method 2 (Hugging Face)
2. ✅ Install dependencies
3. ✅ Download a model
4. ✅ Run examples
5. ✅ Experiment with prompts
6. ⚠️ **Verify all chemical data against real sources**

---

## Support

If you encounter issues:

1. Check [Troubleshooting](#troubleshooting) section
2. Review Ollama docs: https://ollama.ai/
3. Check model requirements on Hugging Face
4. Verify Python and GPU driver versions

---

## Remember

🧪 **You're a chemist** - Trust your knowledge over AI output!

These tools are for:
- ✅ Literature research assistance
- ✅ Chemical reasoning help
- ✅ Learning about AI limitations
- ❌ **NOT** for generating real analytical data

**Always verify with real sources before formulating!**
