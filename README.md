# Khollelab

Khollelab est le socle d'une salle de colle numérique : une interface sobre pour réfléchir, démontrer et, bientôt, recevoir l'intervention d'un professeur au bon moment.

## Architecture

```text
Browser
  ↓
Next.js (UI et proxy `/api/*`)
  ↓
FastAPI
  ↓
PostgreSQL 17
```

Coolify route le domaine public uniquement vers le port interne `3000` de Next.js. Aucun service ne publie de port hôte. Next.js relaie les URL relatives `/api/*` au backend sur le réseau Docker ; FastAPI vérifie réellement PostgreSQL avec `SELECT 1`. Le backend est structuré pour recevoir ultérieurement modèles, schémas et services métier, sans anticiper leurs schémas.

## Développement local

Prérequis : Docker avec Docker Compose v2.

```bash
cp .env.example .env
# Remplacez au minimum POSTGRES_PASSWORD et le mot de passe dans DATABASE_URL
docker compose up --build
```

Une fois les trois services `healthy`, l'application n'est volontairement liée à aucun port hôte. Pour un accès local ponctuel, utilisez par exemple `docker compose exec frontend wget -qO- http://localhost:3000/`. En déploiement :

- application : le domaine Coolify affecté au service `frontend`, port interne `3000` ;
- API (interne à Docker par défaut) : `http://backend:8000/api/health` ;
- documentation API (interne) : `http://backend:8000/docs`.

Pour arrêter l'application : `docker compose down`. Ajoutez `-v` uniquement si vous souhaitez aussi supprimer les données PostgreSQL.

## Configuration

| Variable | Rôle | Exemple local |
| --- | --- | --- |
| `APP_ENV` | Environnement de l'API | `development` |
| `POSTGRES_DB` | Base créée par PostgreSQL | `khollelab` |
| `POSTGRES_USER` | Utilisateur PostgreSQL | `khollelab` |
| `POSTGRES_PASSWORD` | Secret PostgreSQL (à remplacer) | aucune valeur réelle versionnée |
| `DATABASE_URL` | URL SQLAlchemy avec driver psycopg | `postgresql+psycopg://…@postgres:5432/khollelab` |
| `CORS_ORIGINS` | Origines autorisées, séparées par des virgules | `http://localhost:3000` |
| `INTERNAL_API_URL` | Adresse privée utilisée uniquement par le proxy Next.js | `http://backend:8000` |

`.env.example` ne contient que des valeurs de développement. Ne commitez jamais `.env` ni un secret de production. Les migrations futures pourront être créées et appliquées via `alembic revision --autogenerate` puis `alembic upgrade head` dans `backend/`.

## Déploiement Coolify

1. Créez une ressource **Docker Compose** et connectez ce dépôt Git.
2. Définissez `POSTGRES_DB`, `POSTGRES_USER`, un `POSTGRES_PASSWORD` fort et `DATABASE_URL` avec les mêmes identifiants et l'hôte `postgres`.
3. Définissez `APP_ENV=production`, `INTERNAL_API_URL=http://backend:8000` et `CORS_ORIGINS=https://votre-domaine`.
4. Exposez uniquement le service `frontend` sur le port `3000`, puis associez-lui votre domaine et TLS dans Coolify.
5. Laissez `backend` et `postgres` sans domaine : ils communiquent sur le réseau Compose interne. Le volume nommé `postgres_data` assure la persistance.

Le fichier Compose n'utilise ni chemin absolu, ni bind mount local, ni `localhost` entre conteneurs.

## Contrôles qualité

```bash
cd frontend && npm run lint && npm run build
cd backend && python -m compileall app && pytest
docker compose config
```

## Périmètre PR1

Cette version fournit l'UI responsive, KaTeX, la connectivité et l'infrastructure. Elle n'inclut volontairement ni authentification, ni banque d'exercices réelle, ni correction, ni évaluation LLM.

## Corpus PR2

Les exercices sont des fichiers YAML versionnés sous `problems/`, validés strictement au démarrage puis chargés une seule fois en mémoire. PostgreSQL est réservé aux futures données utilisateur. L'API publique fournit le catalogue (`GET /api/problems`) et le détail (`GET /api/problems/{id}`), mais ne transmet jamais `reference_solution`.

Commandes utiles :

```bash
make test              # tests backend et frontend
make validate-corpus   # validation des YAML avec le chargeur de production
make build             # construction Compose
make smoke             # pile complète et assertions HTTP
```

## LLM examiner runtime configuration
The backend-only examiner uses runtime variables `LLM_PROVIDER`, `LLM_MODEL`,
`OPENAI_API_KEY`, and `LLM_TIMEOUT_SECONDS` (default 90). CI and smoke tests use
`LLM_PROVIDER=fake`. Never expose the key as a build-time or `NEXT_PUBLIC_` variable.

## Inférence distante Hugging Face

La production utilise exclusivement `HuggingFaceProvider` via le routeur OpenAI-compatible `https://router.huggingface.co/v1`. Qwen (Nscale) est la famille par défaut; Gemma (DeepInfra) est sélectionnable côté serveur. Aucun compte Nscale ou DeepInfra séparé n'est nécessaire lorsque routage et facturation passent par Hugging Face.

Configuration Coolify backend :

```dotenv
LLM_PROVIDER=huggingface
HF_TOKEN=<secret>
HF_ROUTER_BASE_URL=https://router.huggingface.co/v1
LLM_MODEL_FAMILY=qwen
HF_QWEN_FAST_MODEL=Qwen/Qwen3-8B:nscale
HF_QWEN_DEEP_MODEL=Qwen/Qwen3-32B:nscale
HF_GEMMA_FAST_MODEL=google/gemma-3-12b-it:deepinfra
HF_GEMMA_DEEP_MODEL=google/gemma-3-27b-it:deepinfra
HF_TIMEOUT_SECONDS=60
```

1. Créez un compte Hugging Face et configurez les crédits/la facturation Inference Providers.
2. Créez un token fin avec la permission **“Make calls to Inference Providers”**, puis enregistrez-le comme secret runtime backend `HF_TOKEN` (jamais `NEXT_PUBLIC_*` ni build arg).
3. Pour Gemma, ouvrez `google/gemma-3-12b-it` et `google/gemma-3-27b-it` connecté à Hugging Face et acceptez les conditions d'utilisation Google Gemma avant tout test.
4. Choisissez `LLM_MODEL_FAMILY=qwen` ou `gemma`, puis redéployez le backend.

CI utilise explicitement `LLM_PROVIDER=fake` et n'effectue aucun appel payant. Les tests réels sont volontaires : `python scripts/smoke_remote_inference.py` et `python scripts/bench_remote_models.py --quick --family all`. Les diagnostics protégés vérifient `/v1/models` sans génération payante et mettent le résultat en cache.
