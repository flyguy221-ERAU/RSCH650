# Contributing to RSCH650 - NTSB/CAROL Accident Analytics

First off, thank you for considering contributing to this project! 🙌
Your contributions help improve aviation safety research and reproducibility.

---

## 📌 Getting Started

### 1. Fork the Repository
Click the **Fork** button on the top right of this repository.

### 2. Clone Your Fork
```bash
git clone https://github.com/<YOUR_GITHUB_USERNAME>/RSCH650-NTSB-CAROL-Accident-Analytics.git
cd RSCH650-NTSB-CAROL-Accident-Analytics
```

### 3. Set Up the Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
pre-commit install
```

### 4. Create a New Branch
```bash
git checkout -b feature/my-new-feature
```

---

## 🛠 Development Guidelines

### **Code Style**
- Use [black](https://black.readthedocs.io/en/stable/) for formatting.
- Use [ruff](https://docs.astral.sh/ruff/) for linting.
- Functions should be **<80 lines** when possible.
- Type hints are **strongly encouraged**.

### **Pre-commit Hooks**
Before committing, make sure hooks pass:
```bash
pre-commit run --all-files
```

### **Running Tests**
```bash
make test
```

### **Makefile Targets**
| Command       | Description                                    |
|--------------|------------------------------------------------|
| `make venv`  | Create `.venv`                                  |
| `make install` | Install dependencies                         |
| `make build` | Run data pipeline → generate Parquet outputs    |
| `make run`   | Start Streamlit app                             |
| `make test`  | Run pytest                                      |
| `make clean` | Remove caches                                  |

---

## ✅ Submitting Changes

1. Commit your changes using descriptive messages:
    ```bash
    git commit -m "Add risk analysis tab with chi-square summaries"
    ```

2. Push your branch:
    ```bash
    git push origin feature/my-new-feature
    ```

3. Open a **Pull Request (PR)** against the `main` branch.

---

## 🧪 Testing New Features

- Add **unit tests** under `tests/`
- Run tests locally before opening a PR:
    ```bash
    make test
    ```

---

## 📊 Data Policy

- Place raw CAROL CSVs in `data/raw/`.
- **Do not commit raw data** to the repository.

---

## 🤝 Code of Conduct

Be respectful and constructive when interacting with others.
This project follows the [Contributor Covenant](https://www.contributor-covenant.org/).

---

## 📚 Questions?

If you have questions about contributing, feel free to **open an issue** or contact:
**Jeremy Scott Feagan** — [jeremy.feagan@gmail.com](mailto:jeremy.feagan@gmail.com)

Thank you for helping make this project better! ✈️
