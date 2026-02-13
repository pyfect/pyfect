# Installation

## Requirements

pyfect requires Python 3.13 or later.

## Install from [PyPI](https://pypi.org/project/pyfect/)

```bash
pip install pyfect
```

## Install from [conda-forge](https://anaconda.org/conda-forge/pyfect)

```bash
conda install conda-forge::pyfect
```

## Install for Development

```bash
git clone https://github.com/pyfect/pyfect.git
cd pyfect
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

## Verify Installation

```python
import pyfect
print(pyfect.__version__)
```
