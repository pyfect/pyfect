# Installation

!!! warning "Early Development"
    pyfect is in active development. The package will be available on PyPI soon.

## Requirements

pyfect requires Python 3.13 or later.

## Install from PyPI (Coming Soon)

```bash
pip install pyfect
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
