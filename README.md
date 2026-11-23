# Medical Triage Multi-Agent System

A multi-agent system that takes patient input and produces a structured report with intake normalization, urgency classification, possible disease categories, reasoning, and cautious treatment-path guidance.

## Safety Note

This repository is for educational and prototyping purposes only.
It is not a medical device, does not provide a real diagnosis, and should not replace a licensed clinician.
If symptoms could represent an emergency, the patient should seek immediate professional care.

## Overview

The system uses four specialized agents that pass text outputs to one another through a coordinator:

1. `Intake Agent`
   Structures user input into a clean intake summary.
2. `Triage Agent`
   Assigns an urgency level and highlights red flags.
3. `Diagnosis Agent`
   Produces a cautious differential diagnosis.
4. `Treatment Agent`
   Generates the final integrated report with general management pathways and next steps.

## Workflow

```text
User Input
   |
   v
Intake Agent
   |
   v
Triage Agent
   |
   v
Diagnosis Agent
   |
   v
Treatment Agent
   |
   v
Final Output
```

## Project Structure

```text
.
|-- config/
|   |-- config.py            # local only, ignored by git
|   `-- mock_config.py       # safe template for GitHub
|-- settings/
|   |-- model_profiles.py    # named model bundles
|   `-- prompt_sets/         # editable prompt directories
|-- outputs/                 # generated reports, ignored by git
|-- src/
|   |-- __init__.py
|   `-- medical_triage_system/
|       |-- agents/
|       |   |-- base_agent.py
|       |   |-- intake_agent.py
|       |   |-- triage_agent.py
|       |   |-- diagnosis_agent.py
|       |   `-- treatment_agent.py
|       |-- coordinator.py
|       |-- llm.py
|       |-- main.py
|       `-- schemas.py
|-- LICENSE
|-- README.md
`-- requirements.txt
```

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Copy the example config:

```bash
copy config\mock_config.py config\config.py
```

3. Edit `config/config.py` and add your API key.
4. Choose the active model profile and prompt set in `config/config.py`.

## Experiment Config

Model and prompt tuning now live in `settings/`:

- `settings/model_profiles.py` defines reusable model combinations
- `settings/prompt_sets/default/` stores the current agent prompts
- `config/config.py` selects which model profile and prompt set are active

To test a new prompt version, copy `settings/prompt_sets/default/` into a new folder and switch `ACTIVE_PROMPT_SET`.

## Run

```bash
python -m src.medical_triage_system.main --age "21" --sex "female" --vitals "Temp 38.3C, HR 108, BP 110/70, SpO2 98%" --symptoms "Fever, sore throat, fatigue, swollen neck glands" --history "No chronic illness" --medications "Ibuprofen as needed" --allergies "Penicillin" --duration "3 days"
```

## Web App

Run the local web interface with:

```bash
uvicorn src.medical_triage_system.web_app:app --reload
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000).

The page lets you:

- enter a patient case
- choose a model profile
- choose a prompt set
- review the full outputs from all four agents in one place

## Output

Each run creates a folder inside `outputs/` containing:

- `01_intake_report.md`
- `02_triage_report.md`
- `03_diagnosis_report.md`
- `04_final_report.md`
- `pipeline_summary.json`

## Why This Design Works

- Each agent has a single responsibility.
- The pipeline is easy to inspect and debug because every handoff is saved.
- Triage is separated from diagnosis, which is safer and easier to reason about.
- The final report integrates all previous stages into a single patient-facing summary.

## Testing

```bash
pip install -r requirements-dev.txt
ruff check .
pytest -v
```

Tests replace the LLM client with a fake, so they run offline and cost nothing.

## Docker

```bash
docker build -t medical-triage .
docker run -p 8080:8080 \
  -e PROVIDER_3_API_KEY=sk-... \
  -e PROVIDER_3_BASE_URL=https://your-provider/v1 \
  -e ACTIVE_MODEL_PROFILE=model_3 \
  medical-triage
```

Open [http://localhost:8080](http://localhost:8080). Provider settings can come from `config/config.py` or from
`<PROVIDER_NAME>_API_KEY` / `<PROVIDER_NAME>_BASE_URL` environment variables (env vars win).

## Kubernetes

Manifests live in `k8s/`:

| File | What it does |
| --- | --- |
| `configmap.yaml` | Non-secret settings (model profile, prompt set) injected as env vars |
| `deployment.yaml` | Runs 2 replicas with readiness/liveness probes on `/api/health`, resource limits, non-root user, read-only root filesystem, and zero-downtime rolling updates |
| `service.yaml` | Stable ClusterIP address that load-balances across ready pods |

API keys go in a Secret named `llm-credentials` (optional; pods start without it).

### Run locally with minikube (macOS)

```bash
brew install minikube kubectl          # needs Docker Desktop running
minikube start

eval $(minikube docker-env)            # build straight into minikube's Docker
docker build -t medical-triage:local .

kubectl create secret generic llm-credentials \
  --from-literal=PROVIDER_3_API_KEY=sk-... \
  --from-literal=PROVIDER_3_BASE_URL=https://your-provider/v1   # optional

kubectl apply -f k8s/
kubectl rollout status deployment/medical-triage
kubectl port-forward svc/medical-triage 8080:80   # open http://localhost:8080
```

Things to try:

```bash
kubectl get pods                                   # see the 2 replicas
kubectl scale deployment/medical-triage --replicas=3
kubectl delete pod <pod-name>                      # watch Kubernetes replace it
kubectl logs -l app=medical-triage --tail=20
minikube delete                                    # clean up
```

CI runs the same flow on every push in a throwaway [kind](https://kind.sigs.k8s.io/) cluster:
deploy, smoke-test through the Service, scale to 3 replicas, and verify self-healing after a pod is deleted.

## CI/CD

`.github/workflows/ci-cd.yml` runs on every push and pull request:

1. **Lint & test**: `ruff` + `pytest`
2. **Build & smoke-test**: builds the Docker image, starts it, and checks `/api/health`
3. **Kubernetes**: deploys to a kind cluster, smoke-tests via the Service, scales, and checks self-healing
4. **Deploy** (main branch only): pushes the image to Artifact Registry and deploys to Cloud Run

The deploy job is skipped until GCP is configured. To enable it:

- Repository variable `GCP_PROJECT_ID` (optional: `GCP_REGION`, `GCP_ARTIFACT_REPO`, `CLOUD_RUN_SERVICE`)
- Repository secret `GCP_SA_KEY`: service-account JSON with Cloud Run Admin, Artifact Registry Writer,
  Service Account User, and Secret Manager Secret Accessor roles
- Secret Manager secrets `provider-3-api-key` and `provider-3-base-url`
